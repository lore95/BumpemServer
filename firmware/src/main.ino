/*************************************************************
 *  BUMP'EM FIRMWARE v1 — Teensy 4.1, 4 cable modules (A–D)
 *
 *  Serial protocol v1: docs/PROTOCOL.md (single source of truth).
 *  Parameter defaults reproduce the v0 firmware (legacy/Arduino_Script.ino).
 *
 *  The board knows channels, forces and times only. Angles, gait events,
 *  PTO and sequences are computed on the host.
 *************************************************************/

#include <Wire.h>
#include <Adafruit_MCP4728.h>

#define FW_VERSION  "1.0.0"
#define N_CH        4
#define F_HARD_MAX  200.0f    // N, ceiling for fmax_n (thesis §2.10)
#define ADC_MAX     1023.0f   // 10-bit (v0 .ino:39)
#define DAC_MAX     4095
#define D_WIN_MAX   8
#define LINE_MAX    128

Adafruit_MCP4728 Driver;

// ============================================================
//  CHANNELS (pins from v0 .ino:45-63, docs/knowledge/hardware.md)
// ============================================================
const char CH_NAME[N_CH]   = {'A', 'B', 'C', 'D'};
const int  PIN_FORCE[N_CH]  = {A0, A1, A2, A3};
const int  PIN_ENABLE[N_CH] = {27, 28, 29, 30};
const MCP4728_channel_t DAC_CH[N_CH] = {MCP4728_CHANNEL_A, MCP4728_CHANNEL_B,
                                        MCP4728_CHANNEL_C, MCP4728_CHANNEL_D};

// ============================================================
//  PARAMETERS (SET/GET). Defaults = v0.
// ============================================================
float loop_ms = 10, kp_track = 0.24, kd_track = 3.5, kp_pulse = 0.24, kd_pulse = 3.5;
float kff = 7.5, rc = 0.01905, kt = 0.1524, i_full = 30, f_full = 200;
float baseline_n = 5, fmax_n = 200, fault_n = 195, fault_ms = 20;
float filter_hz = 0, d_window = 1, arm_ms = 2000, pulse_max_ms = 1000;
float tel_div = 1, wd_ms = 0;
float ch_en[N_CH]  = {1, 1, 1, 0};           // D out of service
float cal_gain[N_CH] = {1, 1, 1, 1};
float cal_off[N_CH]  = {0, 0, 0, 0};

struct Param { const char *name; float *ptr; float lo, hi; bool disarmed_only; };
const Param PARAMS[] = {
  {"loop_ms", &loop_ms, 1, 50, true},
  {"kp_track", &kp_track, 0, 100, false}, {"kd_track", &kd_track, 0, 100, false},
  {"kp_pulse", &kp_pulse, 0, 100, false}, {"kd_pulse", &kd_pulse, 0, 100, false},
  {"kff", &kff, 0, 20, false}, {"rc", &rc, 0.001, 0.2, false}, {"kt", &kt, 0.001, 10, false},
  {"i_full", &i_full, 1, 100, false}, {"f_full", &f_full, 1, 1000, false},
  {"baseline_n", &baseline_n, 0, 30, false}, {"fmax_n", &fmax_n, 0, F_HARD_MAX, false},
  {"fault_n", &fault_n, 0, F_HARD_MAX, false}, {"fault_ms", &fault_ms, 1, 1000, false},
  {"filter_hz", &filter_hz, 0, 500, false}, {"d_window", &d_window, 1, D_WIN_MAX, false},
  {"arm_ms", &arm_ms, 0, 10000, false}, {"pulse_max_ms", &pulse_max_ms, 1, 5000, false},
  {"tel_div", &tel_div, 0, 1000, false}, {"wd_ms", &wd_ms, 0, 60000, false},
  {"ch_A", &ch_en[0], 0, 1, true}, {"ch_B", &ch_en[1], 0, 1, true},
  {"ch_C", &ch_en[2], 0, 1, true}, {"ch_D", &ch_en[3], 0, 1, true},
  {"gain_A", &cal_gain[0], 0.5, 2, false}, {"gain_B", &cal_gain[1], 0.5, 2, false},
  {"gain_C", &cal_gain[2], 0.5, 2, false}, {"gain_D", &cal_gain[3], 0.5, 2, false},
  {"offset_A", &cal_off[0], -20, 20, false}, {"offset_B", &cal_off[1], -20, 20, false},
  {"offset_C", &cal_off[2], -20, 20, false}, {"offset_D", &cal_off[3], -20, 20, false},
};
const int N_PARAMS = sizeof(PARAMS) / sizeof(PARAMS[0]);

// ============================================================
//  STATE
// ============================================================
enum State { DISARMED, ARMING, ARMED, FAULT, RELEASING, ESTOP };
const char *STATE_NAME[] = {"DISARMED", "ARMING", "ARMED", "FAULT", "RELEASING", "ESTOP"};
State state = DISARMED;

enum PulsePhase { P_NONE, P_PENDING, P_ACTIVE, P_ABORTING };
struct Pulse {
  PulsePhase phase;
  uint32_t id, t_start, t_abort;
  float delay, rise, dur, fall, amp[N_CH], abort_level[N_CH];
} pulse = {P_NONE};

// per-channel control state
float f_meas[N_CH], f_filt[N_CH], tgt[N_CH];
float f_hist[N_CH][D_WIN_MAX + 1];      // filtered force history for the D term
int   hist_n = 0;                        // valid samples in history
float bq_b0, bq_b1, bq_b2, bq_a1, bq_a2; // Butterworth coefficients
float bq_x1[N_CH], bq_x2[N_CH], bq_y1[N_CH], bq_y2[N_CH];
uint16_t dac[N_CH];
uint32_t fault_since[N_CH];

uint32_t ramp_t0; float ramp_ms, ramp_from;   // ARMING / RELEASING ramp
uint32_t last_rx_ms, loop_count;
uint32_t loop_us_max, overruns, tx_drops;
bool wd_tripped = false;
elapsedMicros since_tick;

char rx_buf[LINE_MAX]; int rx_len = 0;

// ============================================================
//  OUTPUT (never blocks the control loop for telemetry)
// ============================================================
char *fmt2(char *p, float x) {                 // fixed 2-decimal float, no printf float needed
  long v = lroundf(x * 100.0f);
  if (v < 0) { *p++ = '-'; v = -v; }
  p += sprintf(p, "%ld.%02ld", v / 100, v % 100);
  return p;
}

void emit(const char *line, bool droppable) {
  int n = strlen(line) + 2;
  if (droppable && Serial.availableForWrite() < n) { tx_drops++; return; }
  Serial.print(line); Serial.print("\r\n");
}

void ack_ok(const char *cmd, const char *detail = nullptr) {
  char b[LINE_MAX];
  snprintf(b, sizeof b, detail ? "A,OK,%s,%s" : "A,OK,%s", cmd, detail);
  emit(b, false);
}
void ack_err(const char *cmd, const char *reason) {
  char b[LINE_MAX];
  snprintf(b, sizeof b, "A,ERR,%s,%s", cmd, reason);
  emit(b, false);
}
void event(const char *kind, const char *rest = nullptr) {
  char b[LINE_MAX];
  snprintf(b, sizeof b, rest ? "E,%lu,%s,%s" : "E,%lu,%s", (unsigned long)millis(), kind, rest);
  emit(b, true);                        // may be called mid-loop: never block
}

void set_state(State s) {
  if (s == state) return;
  state = s;
  event("STATE", STATE_NAME[s]);
}

// ============================================================
//  HARDWARE
// ============================================================
void write_outputs() {
  Driver.fastWrite(dac[0], dac[1], dac[2], dac[3]);  // one I²C transaction for all channels
}

void drivers_off() {
  for (int c = 0; c < N_CH; c++) { digitalWrite(PIN_ENABLE[c], LOW); dac[c] = 0; }
  write_outputs();
}

// ============================================================
//  FILTER / CONTROL
// ============================================================
void filter_setup() {
  if (filter_hz <= 0) return;
  float K = tanf(PI * filter_hz * loop_ms / 1000.0f), K2 = K * K;
  float norm = 1.0f / (1.0f + M_SQRT2 * K + K2);
  bq_b0 = K2 * norm; bq_b1 = 2 * bq_b0; bq_b2 = bq_b0;
  bq_a1 = 2 * (K2 - 1) * norm; bq_a2 = (1 - M_SQRT2 * K + K2) * norm;
}

void control_reset() {           // restart filter and D history from the current reading
  for (int c = 0; c < N_CH; c++) {
    float r = analogRead(PIN_FORCE[c]) / ADC_MAX * f_full * cal_gain[c] + cal_off[c];
    bq_x1[c] = bq_x2[c] = bq_y1[c] = bq_y2[c] = r;
    for (int k = 0; k <= D_WIN_MAX; k++) f_hist[c][k] = r;
  }
  hist_n = D_WIN_MAX + 1;
  filter_setup();
}

float filter_step(int c, float x) {
  if (filter_hz <= 0) return x;
  float y = bq_b0 * x + bq_b1 * bq_x1[c] + bq_b2 * bq_x2[c] - bq_a1 * bq_y1[c] - bq_a2 * bq_y2[c];
  bq_x2[c] = bq_x1[c]; bq_x1[c] = x; bq_y2[c] = bq_y1[c]; bq_y1[c] = y;
  return y;
}

bool pulse_drives_gains() { return pulse.phase == P_ACTIVE || pulse.phase == P_ABORTING; }

// Pulse amplitude contribution on channel c at time now (0 outside a pulse)
float pulse_amp(int c, uint32_t now) {
  if (pulse.phase == P_ACTIVE) {
    float e = now - pulse.t_start, a = pulse.amp[c];
    if (e < pulse.rise) return a * e / pulse.rise;
    if (e < pulse.dur - pulse.fall) return a;
    if (e < pulse.dur) return a * (pulse.dur - e) / pulse.fall;
    return 0;
  }
  if (pulse.phase == P_ABORTING) {
    float e = now - pulse.t_abort;
    if (pulse.fall <= 0 || e >= pulse.fall) return 0;
    return pulse.abort_level[c] * (1 - e / pulse.fall);
  }
  return 0;
}

void pulse_update(uint32_t now) {
  char id[16]; snprintf(id, sizeof id, "%lu", (unsigned long)pulse.id);
  if (pulse.phase == P_PENDING && (int32_t)(now - pulse.t_start) >= 0) {
    pulse.phase = P_ACTIVE;
    event("PSTART", id);
  }
  if (pulse.phase == P_ACTIVE && now - pulse.t_start >= pulse.dur) {
    pulse.phase = P_NONE;
    event("PEND", id);
  }
  if (pulse.phase == P_ABORTING && (pulse.fall <= 0 || now - pulse.t_abort >= pulse.fall)) {
    pulse.phase = P_NONE;
  }
}

void pulse_abort(uint32_t now) {
  if (pulse.phase == P_NONE || pulse.phase == P_ABORTING) return;
  char id[16]; snprintf(id, sizeof id, "%lu", (unsigned long)pulse.id);
  if (pulse.phase == P_ACTIVE) {
    for (int c = 0; c < N_CH; c++) pulse.abort_level[c] = pulse_amp(c, now);
    pulse.t_abort = now;
    pulse.phase = P_ABORTING;
  } else {
    pulse.phase = P_NONE;
  }
  event("PABORT", id);
}

// Baseline level for the current state (ARMING/RELEASING ramps)
float state_level(uint32_t now) {
  switch (state) {
    case ARMED: case FAULT: return baseline_n;
    case ARMING: case RELEASING: {
      float e = now - ramp_t0;
      float to = (state == ARMING) ? baseline_n : 0;
      if (ramp_ms <= 0 || e >= ramp_ms) return to;
      return ramp_from + (to - ramp_from) * e / ramp_ms;
    }
    default: return 0;
  }
}

void control_step(uint32_t now) {
  int m = (int)d_window;
  bool in_pulse = pulse_drives_gains();
  float kp = in_pulse ? kp_pulse : kp_track, kd = in_pulse ? kd_pulse : kd_track;
  float level = state_level(now);
  bool driving = (state == ARMED || state == FAULT || state == ARMING || state == RELEASING);

  for (int c = 0; c < N_CH; c++) {
    f_meas[c] = analogRead(PIN_FORCE[c]) / ADC_MAX * f_full * cal_gain[c] + cal_off[c];
    f_filt[c] = filter_step(c, f_meas[c]);
    for (int k = D_WIN_MAX; k > 0; k--) f_hist[c][k] = f_hist[c][k - 1];
    f_hist[c][0] = f_filt[c];

    if (!driving || ch_en[c] < 0.5f) {
      tgt[c] = 0; dac[c] = 0;
      digitalWrite(PIN_ENABLE[c], LOW);
      continue;
    }
    tgt[c] = min(level + pulse_amp(c, now), fmax_n);     // firmware clamp, whatever the host sends

    float d = (f_filt[c] - f_hist[c][m]) / (m * loop_ms);  // N/ms, as v0
    float ides = kp * (tgt[c] - f_filt[c]) - kd * d + kff * tgt[c] * rc / kt;
    float u = constrain(ides / i_full, 0.0f, 1.0f);
    dac[c] = (uint16_t)(u * DAC_MAX);
    digitalWrite(PIN_ENABLE[c], HIGH);

    // over-force fault
    if (fault_n > 0 && f_meas[c] >= fault_n) {
      if (!fault_since[c]) fault_since[c] = now ? now : 1;
      else if (now - fault_since[c] >= fault_ms && state == ARMED) {
        pulse_abort(now);
        char b[32]; char *p = b + sprintf(b, "%c,", CH_NAME[c]); fmt2(p, f_meas[c]);
        event("FAULT", b);
        set_state(FAULT);
      }
    } else {
      fault_since[c] = 0;
    }
  }
  write_outputs();

  if (state == ARMING && now - ramp_t0 >= ramp_ms) set_state(ARMED);
  if (state == RELEASING && now - ramp_t0 >= ramp_ms) { drivers_off(); set_state(DISARMED); }
}

void telemetry(uint32_t now) {
  if (tel_div < 1 || loop_count % (uint32_t)tel_div) return;
  char b[256]; char *p = b;
  p += sprintf(p, "T,%lu,%s,%lu", (unsigned long)now, STATE_NAME[state],
               (unsigned long)(pulse.phase == P_NONE ? 0 : pulse.id));
  for (int c = 0; c < N_CH; c++) {
    *p++ = ','; p = fmt2(p, tgt[c]);
    *p++ = ','; p = fmt2(p, f_meas[c]);
    p += sprintf(p, ",%u", dac[c]);
  }
  *p = 0;
  emit(b, true);
}

// ============================================================
//  COMMANDS
// ============================================================
int split(char *s, char **tok, int max) {
  int n = 0;
  for (char *t = strtok(s, " \t"); t && n < max; t = strtok(nullptr, " \t")) tok[n++] = t;
  return n;
}

bool parse_num(const char *s, float *out) {
  char *end; *out = strtof(s, &end);
  return end != s && *end == 0;
}

void upcase(char *s) { for (; *s; s++) *s = toupper(*s); }

const Param *find_param(const char *name) {
  for (int i = 0; i < N_PARAMS; i++) if (!strcasecmp(PARAMS[i].name, name)) return &PARAMS[i];
  return nullptr;
}

void print_param(const Param *p) {
  char b[64]; char *q = b + sprintf(b, "P,%s,", p->name);
  dtostrf(*p->ptr, 0, 5, q);            // 5 decimals: enough for rc/kt
  emit(b, false);
}

void cmd_pulse(char **tok, int n, uint32_t now) {
  if (n != 10) { ack_err("PULSE", "usage: PULSE id delay rise dur fall aA aB aC aD"); return; }
  if (state != ARMED) { ack_err("PULSE", "not armed"); return; }
  if (pulse.phase != P_NONE) { ack_err("PULSE", "busy"); return; }
  float v[9];
  for (int i = 0; i < 9; i++) if (!parse_num(tok[i + 1], &v[i])) { ack_err("PULSE", "bad number"); return; }
  float delay = v[1], rise = v[2], dur = v[3], fall = v[4];
  if (v[0] < 1) { ack_err("PULSE", "id must be >= 1"); return; }
  if (delay < 0 || delay > 10000) { ack_err("PULSE", "delay out of range"); return; }
  if (rise < 0 || fall < 0 || dur <= 0 || rise + fall > dur) { ack_err("PULSE", "need rise+fall <= dur"); return; }
  if (dur > pulse_max_ms) { ack_err("PULSE", "dur > pulse_max_ms"); return; }
  for (int c = 0; c < N_CH; c++) {
    float a = v[5 + c];
    if (a < 0) { ack_err("PULSE", "negative amplitude"); return; }
    if (a > 0 && ch_en[c] < 0.5f) { ack_err("PULSE", "channel disabled"); return; }
    if (baseline_n + a > fmax_n) { ack_err("PULSE", "exceeds fmax_n"); return; }
  }
  pulse.id = (uint32_t)v[0];
  pulse.delay = delay; pulse.rise = rise; pulse.dur = dur; pulse.fall = fall;
  for (int c = 0; c < N_CH; c++) pulse.amp[c] = v[5 + c];
  pulse.t_start = now + (uint32_t)delay;
  pulse.phase = P_PENDING;
  char d[16]; snprintf(d, sizeof d, "%lu", (unsigned long)pulse.id);
  ack_ok("PULSE", d);
}

void handle_line(char *line, uint32_t now) {
  char *tok[12];
  int n = split(line, tok, 12);
  if (n == 0) return;
  upcase(tok[0]);
  const char *cmd = tok[0];

  if (!strcmp(cmd, "PING")) { ack_ok(cmd); }
  else if (!strcmp(cmd, "INFO")) {
    char b[LINE_MAX];
    snprintf(b, sizeof b, "I,proto=1,fw=%s,board=teensy41,channels=%d,f_hard_max=200", FW_VERSION, N_CH);
    emit(b, false); ack_ok(cmd);
  }
  else if (!strcmp(cmd, "STATS")) {
    char b[LINE_MAX];
    snprintf(b, sizeof b, "I,loop_us_max=%lu,overruns=%lu,tx_drops=%lu,uptime_ms=%lu",
             (unsigned long)loop_us_max, (unsigned long)overruns, (unsigned long)tx_drops,
             (unsigned long)millis());
    emit(b, false); loop_us_max = 0; ack_ok(cmd);
  }
  else if (!strcmp(cmd, "GET")) {
    if (n == 1) { for (int i = 0; i < N_PARAMS; i++) print_param(&PARAMS[i]); ack_ok(cmd); }
    else {
      const Param *p = find_param(tok[1]);
      if (!p) { ack_err(cmd, "unknown parameter"); return; }
      print_param(p); ack_ok(cmd);
    }
  }
  else if (!strcmp(cmd, "SET")) {
    if (n != 3) { ack_err(cmd, "usage: SET name value"); return; }
    const Param *p = find_param(tok[1]);
    float v;
    if (!p) { ack_err(cmd, "unknown parameter"); return; }
    if (!parse_num(tok[2], &v)) { ack_err(cmd, "bad number"); return; }
    if (v < p->lo || v > p->hi) { ack_err(cmd, "out of range"); return; }
    if (pulse.phase != P_NONE) { ack_err(cmd, "busy"); return; }
    if (state == ARMING || state == RELEASING) { ack_err(cmd, "busy"); return; }
    if (p->disarmed_only && !(state == DISARMED || state == ESTOP)) { ack_err(cmd, "disarm first"); return; }
    if (p->ptr == &filter_hz && v > 0 && v >= 500.0f / loop_ms) { ack_err(cmd, "filter_hz >= Nyquist"); return; }
    if (p->ptr == &loop_ms && filter_hz > 0 && filter_hz >= 500.0f / v) { ack_err(cmd, "filter_hz >= Nyquist"); return; }
    if (p->ptr == &d_window || p->ptr == &loop_ms || p->ptr == &tel_div) v = roundf(v);
    if ((p->ptr == &baseline_n && v > fmax_n) || (p->ptr == &fmax_n && v < baseline_n)) { ack_err(cmd, "baseline_n > fmax_n"); return; }
    *p->ptr = v;
    if (p->ptr == &filter_hz || p->ptr == &loop_ms) control_reset();
    ack_ok(cmd, p->name);
  }
  else if (!strcmp(cmd, "ARM")) {
    if (state != DISARMED && state != ESTOP) { ack_err(cmd, "already armed"); return; }
    control_reset();
    ramp_t0 = now; ramp_ms = arm_ms; ramp_from = 0;
    set_state(ARMING); ack_ok(cmd);
  }
  else if (!strcmp(cmd, "PULSE")) { cmd_pulse(tok, n, now); }
  else if (!strcmp(cmd, "ABORT")) { pulse_abort(now); ack_ok(cmd); }
  else if (!strcmp(cmd, "RELEASE")) {
    float ms = 1000;
    if (n > 1 && (!parse_num(tok[1], &ms) || ms < 0 || ms > 10000)) { ack_err(cmd, "bad ms"); return; }
    if (state != ARMED && state != FAULT) { ack_err(cmd, "not armed"); return; }
    pulse_abort(now);                   // active pulse ramps down over its fall while releasing
    ramp_from = baseline_n; ramp_t0 = now; ramp_ms = ms;
    set_state(RELEASING); ack_ok(cmd);
  }
  else if (!strcmp(cmd, "ESTOP") || !strcmp(cmd, "STOP")) {
    drivers_off();
    if (pulse.phase != P_NONE) pulse_abort(now);
    pulse.phase = P_NONE;
    set_state(ESTOP); ack_ok("ESTOP");
  }
  else if (!strcmp(cmd, "CLEAR")) {
    if (state != FAULT) { ack_err(cmd, "not in fault"); return; }
    set_state(ARMED); ack_ok(cmd);
  }
  else { ack_err(cmd, "unknown command"); }
}

void read_serial(uint32_t now) {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      rx_buf[rx_len] = 0;
      last_rx_ms = now; wd_tripped = false;
      handle_line(rx_buf, now);
      rx_len = 0;
    } else if (rx_len < LINE_MAX - 1) {
      rx_buf[rx_len++] = ch;
    } else {
      rx_len = 0;                       // overlong line: discard
      ack_err("LINE", "too long");
    }
  }
}

// ============================================================
//  SETUP / LOOP
// ============================================================
void setup() {
  Serial.begin(115200);
  for (int c = 0; c < N_CH; c++) { pinMode(PIN_ENABLE[c], OUTPUT); digitalWrite(PIN_ENABLE[c], LOW); }

  Wire.begin();
  Wire.setClock(400000);
  if (!Driver.begin()) {
    // Cannot drive motors; report forever, drivers stay disabled.
    while (1) { Serial.println("E,0,FAULT,DAC init failed"); delay(1000); }
  }
  for (int c = 0; c < N_CH; c++) Driver.setChannelValue(DAC_CH[c], 0);  // sets VREF=VDD, gain 1x (as v0)
  drivers_off();
  control_reset();
  last_rx_ms = millis();
  emit("I,proto=1,fw=" FW_VERSION ",board=teensy41,channels=4,f_hard_max=200", false);
  event("STATE", STATE_NAME[state]);
}

void loop() {
  uint32_t now = millis();
  read_serial(now);

  // watchdog: host silent → abort any pulse, keep tension (safety.md)
  if (wd_ms > 0 && !wd_tripped && now - last_rx_ms > wd_ms) {
    wd_tripped = true;
    pulse_abort(now);
    event("WD");
  }

  uint32_t period_us = (uint32_t)loop_ms * 1000;
  if (since_tick < period_us) return;
  if (since_tick >= 2 * period_us) { overruns++; since_tick = 0; }
  else since_tick -= period_us;

  elapsedMicros busy;
  now = millis();
  pulse_update(now);
  control_step(now);
  telemetry(now);
  loop_count++;
  if (busy > loop_us_max) loop_us_max = busy;
}
