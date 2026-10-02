## Controller
In this section we outline the general processes we use to build the open-loop and
closed-loop controllers used in the associated ICRA 2020 manuscript.
Controller hardware
We did not provide a recommended controller as there are a large number of options to choose
from, ranging from large real-time machines, to inexpensive microcontrollers. Two key functional
components to consider when choosing a controller are:
1) Input and output ports
Our proposed setup is configured for analog communication to and from the controller.
Your chosen controller should be able to handle the following port requirements
depending on your chosen configuration. Multiply the numbers with the number of
modules you have if you are using a shared controller across modules.
Configuration Analog in Analog out
Open-loop 0 2 (or 1 Analog, 1 Digital):
Motor command & Motor enable
Closed-loop 1: Strain gauge signal 2 (or 1 Analog, 1 Digital):
Motor command & Motor enable

Optional Encoder Additional 1: Encoder signal Additional 0
2) Clock speed
Faster clock speeds will allow faster control loop update rates.
The results shown were collected using a Speedgoat Performance real-time target machine with
IO106 (Analog in) and IO111 (Analog out) boards and running the control loop at 1000Hz. The
newer Teensy boards (3.5 onwards) boast impressive clock speeds that should allow similar
loop rates, depending on the complexity of your code. We have not verified the Teensy
controllers work in this application, but their data sheets indicate they could be a good option to
try.

34

Control architecture
The basic control architectures are shown below: A corresponds to open-loop control and
B corresponds to closed-loop proportional-derivative (PD) control.

Controller

Where fdes

is the desired force, rc

is the radius of the reel drum, kt

is the motor torque constant,

ides
is the desired current, i is the actual current sent to the motor, fout

is the force output from the

Bump’em module, i
ffwd
is the feed-forward current contribution to the desired current, fmeas
is the

force measured from the strain gauge force sensor, ef

is the error in the force, and ipd
is the PD

controller contribution to the desired current.
The left half of the both architectures contain the features that the controller code is in charge of,
and will be the focus of this section. The setup of components in the right half have been
described in previous sections.
Each of the variables in the controller half of the control architecture diagram can be modified if
needed. The following are notes on each of the variables fdes
, rc
, kt, fmeas
, and the PD controller,

and an additional note on the motor driver current regulator gains.
1) Reel drum radius rc
The reel drum design file provided has a radius rc of 0.75in.
Adjusting this will change the mechanical advantage of the motor transmission.
To change the radius, you will need to modify the reel drum CAD file in CAD -> 1) Motor
Unit -> Reel drum. Make sure to check the mating with other parts after the modification.

35

2) Desired force fdes
The system can comfortably apply perturbations of up to 200N for both open-loop and
closed-loop configurations. The commanded force can also be varied over time to apply
arbitrary perturbation force trajectories. The following figures show the corresponding
performances reported in the ICRA 2020 paper.

3) Motor torque constant kt
The torque constant of the motor, kt, is not exactly as defined in the maxon spec sheet
and therefore must be experimentally determined. We found kt_experimental = 0.89*kt_nominal.
You should be able to use the same value. However, you can also check the value for

36

your own motor if there are discrepancies in your system performance that you suspect
could be caused by an inaccurate motor constant.
To check this, we attached the rope to a treadmill handrail and performed several
step-response tests using open-loop control of the motor. If you have a force sensor, or
use our DIY force sensor, you can do this experiment yourself. Essentially you are
looking for the measured steady-state force (pulls of approx 1-2s should suffice) for a
given current command.
The reason for the discrepancy between kt_experimental and kt_nominal

is that the kt_nominal
reported by maxon is a result of a linearized torque constant calculated for the motor for
its ideal operating conditions. We use the motor near stall, which is quite far from its
peak efficiency/power region. Although kt for a brushed motor is fairly constant for
different current inputs/rotational speeds, the same is not true for brushless motors and
as a result, the linearized value provided by maxon does not hold during our
applications. Another point to note is that although the motor specifications state a stall
current of 56.9A, this is again an extrapolated value based on the motor’s performance
closer to the optimal efficiency/power region. In fact magnetic saturation of the motor
begins to set in around 30 A, and therefore buying a different motor driver with higher
current output will not increase the available torque from the motor.
4) Measured force fmeas
Both the force sensor and motor encoder signals (if used) are filtered with a 2nd order
Butterworth filter with a cutoff frequency of 60 Hz prior to being used in any calculation.
You can tune the order and frequency to achieve the best performance for your system.
It is likely that you might have a different ideal filter frequency if your data sampling rate
is far from the 1000Hz we used.
5) PD gains (Only for closed-loop configuration)
The parameter tuning procedure for the closed-loop step response gains is as follows:
Do a series of step-response perturbations on a standing individual. Start with open-loop
(P and D = 0), then increase P until the step response overshoots by 10%, then increase
D until the overshoot is back under 10%, repeat until there are growing oscillations
(instability) in the force output. Once the controller is unstable, reduce the P and D gains
to the best values prior to instability. Test pulls should be the maximum duration you
anticipate using (we used approximately 500ms step responses), as any instability will
grow with time and testing with the longest step input duration improves likelihood of
stability for all pulls. We achieved sufficient performance using the same gains (Kp =
0.21, Kd = 3) for each force step command magnitude, however for more accurate
tracking, one could tune the PD controller for each force magnitude.
6) The current regulator gains of the motor-driver
We selected current regulator gains that worked well for all of the scenarios in which we
tested Bump’em. All recommended parameters listed here were used in conjunction with
the motor driver parameters as setup in the previous section. However, if your system

37

happens to have very different system dynamics (e.g. much longer rope lengths), or you
want to build Bump’em for a very specific experiment and want to try to account for
force-level system dynamics, you can re-tune the current regulator. The previous section
describes how to change the input values. This can be particularly valuable for the
open-loop system that doesn’t have the higher level PD control loop that the force
sensor enables. For the closed-loop system, the current regulator gains and the PD
gains will work in a cascaded control scheme and altering the current-regulator gains will
likely result in needing to retune the force-level PD gains.
Basic controller: Applying a perturbation
The following is some pseudo code for applying a basic step response perturbation.
Pseudo code for basic open-loop control
if (perturb_now)
fdes = perturbation_force
else
fdes = 0 (Or apply low-force tracking, described in next section)
end
ides = fdes * rc
/ kt

This basic control strategy was what we used to obtain the results as presented in the ICRA
2020 paper. However, rise time performance can be improved by applying more aggressive
control schemes. An extreme example of this is a time-based bang-bang control for a
step-response. We managed to achieve 0-90% rise times in the 30-40 ms range (compared to
59ms with just the basic controller) when using a hand-tuned bang-bang controller
(approximately 25 ms maximum current in pulling direction and then 9 ms in maximum reverse
to decelerate the motor drum) but found it to be too sensitive for a general-purpose research
tool. However, if rise-time is critical for you, and you can deal with the sensitivity to changes in
system dynamics by continuously re-tuning the bang-bang controller to different scenarios, it
can be a very worthy path of exploration for the sensorless route.
Pseudo code for PD closed-loop control
filter fmeas
if (perturb_now)
fdes = perturbation_force
else
fdes = 0 (Or apply low-force tracking, described in next section)
end
ef = fdes - filtered_fmeas
derivative_ef = derivative_fdes - derivative_filtered_fmeas (or any other smoothed derivative
1
)

ipd = P gain * ef + D gain * derivative_ef
i
ffwd = fdes * rc
/ kt

38

ides = i
ffwd + ipd
ef,old = ef
1
In the ICRA 2020 work, derivative_filtered_fmeas

term was calculated using a noise-suppressing
numerical differentiation method that averages the derivative of the measured force over the
previous m time steps, we used m = 3:
Notation: Derivative_filtered_fmea at timestep i = Derivative_filtered_f
i
meas

Derivative_filtered_f
i
meas =
(1/m)*(filtered_f
i
meas - filtered_f
i - m
meas)

Described in detail in eq. 29 of Y. Q. Chen and K. L. Moore, “An optimal design of pd-type
iterative learning control with monotonic convergence,” in Proceedings of the IEEE Internatinal
Symposium on Intelligent Control, 2002, pp. 55–60.
Example feature 1: Applying low-force tracking
We apply a constant low force in between perturbations to maintain a minimal amount of slack
in the rope. For the open-loop controller, we can only tune the force. For the closed-loop
controller, we can tune both the force and the PD gains.
Tuning the force level
When a participant moves, if the tracking force is too low, the motor drum’s rotation will lag
behind the motion of the user, causing it to “bounce” against the user as they pull away. To
reduce these bounces as the user moves, increase the tracking force. The following table lists
the tracking forces that worked best for us.

Closed-loop Open-loop
Standing 3N 3N
Walking 12N 3N

We generally try to keep tracking forces as low as possible while still allowing us to achieve
acceptable slack management, since it can affect the user’s standing posture or walking gait. If
this is a big concern and you have more than one module, you can place one on either side of
the participant (for example, to the left and right) so the net force applied when both modules
apply equal tracking force (in opposite directions) sums to zero.
Tuning the PD gains (Closed-loop only)
We used different PD gains for low-force tracking than what we used for perturbations.
We tuned the gains using a similar procedure as mentioned previously. The notable
difference in the procedure is that instead of doing a step-input, we turned on low-force
tracking and had the participant stand or walk while we monitored the tracking accuracy of

39

the commanded force value, and for high-frequency oscillations (instability). The following
table lists the PD gains that worked best for us:

Closed-loop Open-loop
Standing Kp = 0.3, Kd = 1 NA
Walking Kp = 1, Kd = 1 NA

Example feature 2: Applying a virtual spring
The virtual stabilizing (or destabilizing) spring controller takes in a filtered encoder measurement
(See previous section for notes on signal filtering) to estimate the participant’s position on the
treadmill. In software, we store the encoder value when the person is at the center of the
treadmill and later subtract that from every subsequent measurement to make this the “zero
point” of the virtual spring. The person’s position is then mapped to a desired force based on a
saturated spring model:

Our spring model uses a parametrization of the spring from maximum spring length dmax and
spring force saturation fsat, such that virtual spring stiffness ks = fsat/dmax

. This parametrization is
more intuitive and easy to adjust on a per-experiment basis than selecting a spring stiffness. It
also explicitly states the value for the maximum force the controller will command (summed with
a low-force tracking value) which is helpful for safety.
Virtual spring pseudo code below:

40

if d > dmax
: fdes = fsat + flft
elseIf 0 < d < dma x

: fdes = d*ks + flft

else, fdes = flft
Where d is the measured distance, dmax

is the maximum length of the spring, fdes

is the desired

force, fsat
is the force at which the controller will saturate (summed with flft yields the maximum
allowable force), ks

is the spring constant (defined above), and flft

is the desired low-force
tracking force. If using modules pulling in opposite directions on the user, the flft term is a
constant offset for the forces pulling in opposite directions and effectively “cancels out” for the
net force felt by the user, as described in the Applying low-force tracking section.
Recording the measured force, fmeas

, from force sensor, fdes

, and d while a spring is engaged for
about 30s - 1 min as the participant moves back and forth across the range of the spring
enables you to plot the effective spring relationship (see Fig. 4 in ICRA 2020 manuscript). The
control law for the closed-loop virtual spring is the same as for any other closed loop system
(see ICRA 2020 manuscript for details) but now fdes

is a function of the participant’s position on

the treadmill, measured with the encoder, as shown above in pseudo code.
We used the same PD gains for tracking a virtual spring as for the step-input perturbations and
tracking of various force profiles in the results of the ICRA 2020 paper in an effort to show
reasonable performance with a single set of gains not tuned to a specific person or activity.
Spring rendering can be significantly improved by tuning PD gains specifically for tracking a
virtual spring.