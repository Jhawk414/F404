---
title: "A Method of Estimating Pressure Loss Across Flame Holders in High Velocity Streams"
author: "R. K. Kumar"
year: 1980
source: "[[Kumar 1980 - A Method of Estimating Pressure Loss Across Flame Holders in High Velocity Streams.pdf]]"
doi: "10.1080/00102208008946936"
url: "https://doi.org/10.1080/00102208008946936"
journal: "Combustion Science and Technology, Vol. 21, Issue 5-6, pp. 199-203"
organization: "Gas Turbine Research Establishment, Bangalore 560075, India"
type: reference
tags: [afterburner, augmentor, flameholder, pressure-loss, aerothermo, reference]
created: 2026-10-18
updated: 2026-10-18
status: converted
---

# A Method of Estimating Pressure Loss Across Flame Holders in High Velocity Streams

**R. K. KUMAR**  
*Gas Turbine Research Establishment, Bangalore 560075, India*  
*(Received October 2, 1979)*

- **Journal**: *Combustion Science and Technology*, Vol. 21, Issue 5–6, pp. 199–203 (1980)
- **DOI**: [10.1080/00102208008946936](https://doi.org/10.1080/00102208008946936)
- **Copyright**: © 1980 Gordon and Breach Science Publishers, Inc. / Taylor & Francis

---

## ABSTRACT

A simple method has been proposed to estimate the drag coefficient for bluff bodies in high velocity streams. The estimated values for the drag coefficient agrees well with the measured values. The bluff body shapes considered are the flame holder shapes and blockages employed in jet engine after burners. It has been found that over a range of inlet conditions, the drag coefficient remained fairly independent of Reynolds number. An approximate method of estimating the drag coefficient for staggered flame holder is indicated.

---

{199}------------------------------------------------

## 1 INTRODUCTION

A bluff body immersed in a high velocity stream for flame stabilization causes a loss of stagnation pressure and it is of interest to know the pressure loss as a function of approach Mach number, flame holder blockage and shape. Extensive experimental work has been carried out by NASA (1955) and several other organizations (Edwards, 1955; AGARD, 1957) to evaluate the performance of two dimensional flame holders. However, they are only indicative of the trend and it is difficult to accurately estimate the pressure loss from the information provided. Some analytical work has been done by Lefebvre (1965) relating the geometrical blockage to the so-called aerodynamic blockage. It may be possible to establish the drag co-efficients perhaps by the relationship presented. Whether the relationship holds true in a highly turbulent regime is not clear. The range of Reynolds number over which the results may be valid is not reported. Intuitively, it appears reasonable to assume that the aerodynamic blockage would approach the geometrical blockage for a highly turbulent approach flow and the approach suggested by Lefebvre (1965) may not be strictly valid.

Further, the experimental data reported there relates to three dimensional bodies such as hollow cones with apex pointing upstream. It is not a common practice to use three dimensional bodies in afterburner combustion chambers for flame stabilization purposes and in many cases the flame holder has a V-gutter shape with included angles between 30 and 40 degrees. Further, for reasons of good flame spreading and stability, the flame holder consists of several rings of V-gutters staggered and connected together by connecting gutters. In such cases, the total pressure loss appears to be slightly lower than for the non-staggered coplanar arrangement. An empirical relationship is presented in this note to estimate the flame holder loss co-efficient as a function of blockage, gutter shape and stagger.

## 2 EQUATIONS

The standard method of expressing the total pressure loss is in terms of number of dynamic heads of the approach flow as

$$\Delta P = P_{01} - P_{02} = \frac{1}{2} C_D \rho V_1^2 \tag{1}$$

where $P_{01}$ and $P_{02}$ are the entry and the outlet total pressures, and $C_D$ is the loss co-efficient. The definition of $C_D$ here is different from the one that is commonly used in practice, $C_d$, the drag co-efficient which may be expressed as

$$C_d = \frac{A \Delta P}{\frac{1}{2} \rho a V_1^2} = \left(\frac{A}{a}\right) C_D \tag{2}$$

where $a$ is the flame holder projected area and $A$ is the duct area. In the present context Eq. (1) is employed. If $\beta$ denotes the blockage defined as $\beta = (a/A)$, then it has been found that across a flame holder there is a sudden contraction followed by an immediate expansion of the flow. In such a case, if $\alpha$ is the area contraction factor defined as the ratio of minimum flow area at the flame holder edge to the free stream flow area, then the loss co-efficient $C_D$ may be expressed as (Bird et al., 1960):

$$C_D = K (1 - \alpha) \left(\frac{1}{\alpha^2} - 1\right) \tag{3}$$

where $K$ is a constant. For a sharp edge the constant ($K$) has a value of 2.7. Equation (3) is valid for the flow in the turbulent incompressible range and as such should not be applied to cases in which the Mach number of the approach flow is far in excess of 0.3. Normally, in jet engine afterburners, the approach Mach number seldom exceeds the incompressibility limit and the use of Eq. (3) is justified.

{200}------------------------------------------------

In terms of the blockage factor $\beta$, Eq. (3) can be written as

$$C_D = K \frac{\beta^2 (2 - \beta)}{(1 - \beta)^2} \tag{4}$$

where $\beta = 1 - \alpha$.

The flame holders used in afterburners cannot be strictly treated as sharp edges. Furthermore, it has been observed and is also intuitively evident that for a given flame holder projected area, the loss co-efficient $C_D$ depends upon the gutter included angle ($\theta$). To take into account the effect of gutter included angle on $C_D$, the expression is modified as

$$C_D = K \frac{\beta^2 (2 - \beta)}{(1 - \beta)^2} \left[\sin\left(\frac{\theta}{2}\right)\right]^n \tag{5}$$

where $K$ and $n$ are to be found from experiments.

For a gutter included angle of $180^\circ$ (i.e. a circular flat ring) Eq. (5) gives the maximum loss co-efficient. According to Eq. (5), $C_D$ should drop to zero for $\theta = 0$. This result is unrealistic. However, Edwards (1955) has shown that $C_D$ is the lowest for flame holders with $\theta = 0$. Thus, for the range of gutter angles employed in afterburner flame holders, Eq. (5) appears to be physically reasonable.

In the case of staggered flame holders (Figure 1), the stagger ($\xi$) may be defined as the ratio of the distance separating the first and second ring ($L$) to the width of the gutter ($d$): $\xi = L/d$. For small staggers ($\xi \simeq 1$) the loss factor $C_D$ does not change appreciably from the nonstaggered arrangement. For large staggers, that is, $\xi \ge 2$, considerable reduction in $C_D$ is possible. In such cases the total pressure loss ($\Delta P$) can be expressed as

$$\Delta P = \frac{1}{2} C_{D1} \rho_1 V_1^2 + \frac{1}{2} C_{D2} \rho_2 V_2^2 \tag{6}$$

where the subscripts 1 and 2 refer to first and second rings respectively. If $a_1$ and $a_2$ are the blocked areas of the first and second rings then

$$V_2 = \frac{V_1 A}{A - a_1} = \frac{V_1}{1 - \beta_1} \tag{7}$$

and substituting this in Eq. (6) gives

$$\Delta P = \frac{1}{2} \rho V_1^2 \left[ C_{D1} + \frac{C_{D2}}{(1 - \beta_1)^2} \right] = \bar{C}_D \left(\frac{1}{2} \rho V_1^2\right) \tag{8}$$

assuming $\rho_1 = \rho_2$. Here, $\bar{C}_D = C_{D1} + C_{D2}/(1 - \beta_1)^2$ is the effective loss co-efficient. However, $C_{D1}$ and $C_{D2}$ can be expressed in terms of their individual blockage factors as

$$C_{D1} = K \frac{\beta_1^2 (2 - \beta_1)}{(1 - \beta_1)^2} \left[\sin\left(\frac{\theta}{2}\right)\right]^n \tag{9}$$

and

$$C_{D2} = K \frac{\beta_2^2 (2 - 2\beta_1 - \beta_2)}{(1 - \beta_1)(1 - \beta_1 - \beta_2)^2} \left[\sin\left(\frac{\theta}{2}\right)\right]^n \tag{10}$$

The definition of blockage $\beta_2$ is the same as for $\beta_1$, that is, $\beta_2 = (a_2 / A)$. This is the apparent blockage. Since the flame holder wake extends quite far down stream, the effective blockage of the second gutter is $a_2 / (A - a_1)$. Substituting for $C_{D1}$ and $C_{D2}$ in Eq. (8) yields

$$\bar{C}_D = K \left[ \frac{\beta_1^2 (2 - \beta_1)}{(1 - \beta_1)^2} + \frac{\beta_2^2 (2 - 2\beta_1 - \beta_2)}{(1 - \beta_1)^3 (1 - \beta_1 - \beta_2)^2} \right] \left[\sin\left(\frac{\theta}{2}\right)\right]^n \tag{11}$$

It is assumed here that both the flame holders have the same included angle and the area occupied by the first ring is not available to the second.

Where the stagger is very large, the gutters can be considered completely independent of each other and the expression for $\bar{C}_D$ becomes

$$\bar{C}_D = K \left[ \frac{\beta_1^2 (2 - \beta_1)}{(1 - \beta_1)^2} + \frac{\beta_2^2 (2 - \beta_2)}{(1 - \beta_2)^2} \right] \left[\sin\left(\frac{\theta}{2}\right)\right]^n \tag{12}$$

assuming, as before, that both flame holders have the same gutter angle. However, $\bar{C}_D$ expressed by Eq. (12) is unattainable in practice since it assumes very large staggers which are not of practical interest. It is to be noted that the constants $K$ and $n$ are the same for all gutter shapes and blockages. From experiments it has been found that $K = 4$ and $n = 0.5$. Though the method illustrated here is for two-ring flame holders, it can be extended for flame holders with more than two rings.

## 3 EXPERIMENTAL SET-UP

The experiments were carried out in a 20-inch diameter afterburner fitted with an antiscreech liner and spray bars for fuel injection. Measurements of total temperature and pressures were made immediately upstream and considerably down stream of the flame holder. The total pressures were measured by means of ten point rakes. To isolate the pressure losses caused by the liner and spray bars, a series of runs were made with the flame holder removed. From this, a liner loss co-efficient was estimated and to arrive at the total pressure loss due to flame holder only, the loss due to liner and spray bars was subtracted from the total loss.

{201}------------------------------------------------

![Figure 1: Schematic of the afterburner](images/Kumar%201980%20-%20A%20Method%20of%20Estimating%20Pressure%20Loss%20Across%20Flame%20Holders%20in%20High%20Velocity%20Streams/figure-1.png)  
*FIGURE 1: Schematic of the afterburner showing flame holders, stagger distance, duct geometry, and stations 1 and 2.*

## 4 DISCUSSION

Figure 2 shows the total pressure loss plotted as percent of inlet total pressure against the approach Mach number, $M_0$, for a three ring flame holder with a blocked area of approximately thirty percent of the duct area. The computed value of $C_D$ is 0.69 as against 0.7 used in Figure 2 for comparison with experimentally measured values of $\Delta P / P_{01}$. The gutter included angle in this case is 30 degrees. It appears that a single value of $C_D$ tends to deviate the calculated $\Delta P / P_{01}$ from the measured value at high Mach numbers. Here, $\Delta P / P_{01}$ is calculated from the relationship

$$\frac{\Delta P}{P_{01}} = \frac{1}{2} C_D \gamma M_0^2 \left( 1 + \frac{\gamma - 1}{2} M_0^2 \right)^{-\frac{\gamma}{\gamma - 1}} \tag{13}$$

However, for Mach numbers exceeding 0.3, the fluid cannot be assumed incompressible and $\Delta P / P_{01}$ has to be found by applying the equations of continuity and momentum across the flame-holder. The expression for $\Delta P / P_{01}$ is

$$\frac{\Delta P}{P_{01}} = \frac{\frac{p_2}{P_{02}} \left(M_0'^2 + \frac{1}{\gamma}\right) - \frac{p_1}{P_{02}} \left(M_0^2 + \frac{1}{\gamma} - \frac{1}{2} C_D M_0^2\right)}{\frac{p_2}{P_{02}} \left(M_0'^2 + \frac{1}{\gamma}\right)} \tag{14}$$

![Figure 2: Pressure loss across three ring V-gutter](images/Kumar%201980%20-%20A%20Method%20of%20Estimating%20Pressure%20Loss%20Across%20Flame%20Holders%20in%20High%20Velocity%20Streams/figure-2.png)  
*FIGURE 2: Pressure loss across three ring V-gutter ($\beta = 0.307$, included angle $\theta = 30^\circ$, theoretical $C_D = 0.69$, best fit $C_D = 0.70$). Solid line: compressible flow equations (Eq. 14); points: measured data and incompressible formulation (Eq. 13).*

The solid line in Figure 2 is computed from Eq. (14) for a $C_D$ of 0.7 and as can be readily seen computation of $\Delta P / P_{01}$ this way agrees better with the experiments. The three ring gutter for which the calculation was done had three rings with mean diameters 14.75, 9.00 and 3.4 inches and a gutter width of 1 inch. The connecting gutters had a total projected area of 11 square inches, so that the total projected area of the flame holder was 96 square inches. For a 20-inch diameter duct this produced a blockage of 30.7 percent.

Figure 3 is a plot of $\Delta P / P_{01}$ against $M_0$ for a blocked area of 38 percent and an angle of 25 degrees. The value predicted for $C_D$ from equations is 1.13 as against a $C_D$ of 1.03 arrived at for best agreements with experimentally measured values of $\Delta P / P_{01}$. There appears to be some discrepancy in this case to the extent of 10 percent. It has been found that for many other flame holders not reported herein the differences between the calculated and best fit $C_D$ values were generally of this order.

{202}------------------------------------------------

![Figure 3: Pressure loss across two ring V-gutter](images/Kumar%201980%20-%20A%20Method%20of%20Estimating%20Pressure%20Loss%20Across%20Flame%20Holders%20in%20High%20Velocity%20Streams/figure-3.png)  
*FIGURE 3: Pressure loss across two ring V-gutter ($\beta = 0.38$, included angle $\theta = 25^\circ$, theoretical $C_D = 1.13$, best fit $C_D = 1.03$).*

![Figure 4: Effect of stagger on total pressure loss](images/Kumar%201980%20-%20A%20Method%20of%20Estimating%20Pressure%20Loss%20Across%20Flame%20Holders%20in%20High%20Velocity%20Streams/figure-4.png)  
*FIGURE 4: Effect of stagger on total pressure loss. Curve 1: 0" stagger ($C_D = 0.47$, theory $0.48$); Curve 2: 2" stagger ($C_D = 0.46$, theory $0.48$); Curve 3: 4" stagger ($C_D = 0.37$, theory $0.34$).*

Figure 4 shows the effect of stagger upon pressure loss. The values of $C_D$ quoted are the mean values. Solid lines are drawn to pass through the experimental points. For small staggers for which $\xi \simeq 1$, the differences in pressure loss between staggered and non-staggered arrangements is small at low Mach numbers. This would indicate that for low staggers, the effective blockage is the same for both staggered and non-staggered gutters. The main factor that influences $C_D$ is the gutter edge gas velocity and for 4-inch stagger ($\xi \simeq 3$), gutter edge velocity would be less than that for a flame holder with small stagger. Curve (3) of Figure 4 is plotted for a stagger of 4 inches and as can be seen, the effect of stagger is quite significant. The reduction in $C_D$ from the non-staggered arrangement is over 20 percent. If one computes an effective blockage for this $C_D$ of 0.37 it works out to be approximately 24.5 percent as against a blockage of 27 percent for zero stagger case. It is to be noted that $C_D$ depends very strongly upon the blockage and a one percent error in the measurement of blocked area results in approximately 10 percent error in the estimation of $C_D$.

For the staggered flame holder reported here, the outer ring had an area of 62.2 in$^2$ and the inner ring 23 in$^2$ with a gutter angle of 30 degrees and the inner ring is located first. Since the expression for $C_D$ is not symmetrical in $\beta_1$ and $\beta_2$, one should be cautious in using the blockages. For very large staggers the expression for $C_D$ becomes symmetrical in $\beta_1$ and $\beta_2$ and which gutter is introduced into the stream first should not matter in computing $C_D$.

In the zero stagger case the computed $C_D$ is 0.48 as compared with the best fit value of 0.466 [Figure 4 legend notes 0.47]. For 4-inch stagger the computed $C_D$ is 0.34 as against 0.37 shown in Figure 4. These represent approximately 3 to 10 percent difference between computed and measured values.

Figure 5 shows the measured variation of $C_d$ with Reynolds number of the approach flow. One would normally expect a reduction in the drag or loss coefficient with increasing Reynolds number. However, since the approach flow is highly turbulent, the drag coefficient has virtually remained independent of the Reynolds number.

{203}------------------------------------------------

![Figure 5: Effect of Reynolds number on the drag coefficient of two ring V-gutter](images/Kumar%201980%20-%20A%20Method%20of%20Estimating%20Pressure%20Loss%20Across%20Flame%20Holders%20in%20High%20Velocity%20Streams/figure-5.png)  
*FIGURE 5: Effect of Reynolds number on the drag coefficient $C_d$ of two ring V-gutter over $N_{RE} = 5\times 10^5$ to $13\times 10^5$.*

Though one cannot say with certainty that $C_D$ is independent of Reynolds number, over the range tested, for flame holders of several shapes and sizes, $C_D$ is nearly independent of Reynolds number. This has been found to be true for many other flame holder shapes not reported here.

In the calculation of $\Delta P / P_{01}$ it has been tacitly assumed that the velocity profile at the entry to the flame holder is uniform. Measurements have shown that this is not the case. The velocity profile was markedly peaked towards the centre. Apparently, this did not affect the pressure loss calculations. In an actual jet engine afterburner the velocity profile, in general, is not uniform and the present investigations afford a means of computing the flame holder pressure losses to a fair degree of accuracy without going into the details of fluid flow.

## 5 CONCLUSIONS

1. A simple empirical relationship relating the flame holder blockage and the gutter included angle gives a reasonably good prediction of loss coefficients over the range encountered in afterburners.
2. Staggering of the flame holders between two to four gutter widths may result in considerable reduction in loss of total pressure.
3. The loss coefficients are nearly independent of Reynolds number over the range tested.

## NOMENCLATURE

| Symbol | Definition |
| :--- | :--- |
| $A$ | Duct flow area |
| $a$ | Flame holder projected area |
| $a_1$ | Projected area of the first ring |
| $a_2$ | Projected area of the second ring |
| $C_d$ | Drag coefficient, $A \Delta P / (\frac{1}{2} \rho a V_1^2) = (A/a) C_D$ |
| $C_D$ | Loss coefficient, $\Delta P / (\frac{1}{2} \rho V_1^2)$ |
| $\bar{C}_D$ | Effective loss coefficient for multi-ring / staggered flame holder |
| $d$ | Gutter width |
| $K$ | Empirical constant ($K = 4.0$ for V-gutters; $2.7$ for sharp edges) |
| $L$ | Distance of axial stagger |
| $M_0$ | Approach Mach number (free stream) |
| $M_0'$ | Downstream Mach number |
| $n$ | Empirical exponent ($n = 0.5$ for V-gutters) |
| $P$ | Stagnation pressure |
| $p$ | Static pressure |
| $V$ | Velocity |

### Subscripts

| Subscript | Definition |
| :--- | :--- |
| $1$ | Upstream of flame holder |
| $2$ | Downstream of flame holder |
| $0$ | Stagnation condition |

### Greek Symbols

| Symbol | Definition |
| :--- | :--- |
| $\alpha$ | Area contraction factor |
| $\beta$ | Geometrical blockage ratio, $(a / A)$ |
| $\Delta$ | Difference |
| $\xi$ | Stagger parameter, $L / d$ |
| $\theta$ | Gutter included angle |
| $\gamma$ | Ratio of specific heats ($c_p / c_v$) |

## REFERENCES

- AGARD (1957). *Combustion Researches and Reviews*, Butterworths Scientific Publications, London.
- Bird, R. B., Stewart, W. E. and Light Foot, E. N. (1960). *Transport Phenomena*, pp. 217–225, John Wiley & Sons, Inc.
- Edwards, J. L. (1955). Reheat for gas turbines. *Journal of Royal Aeronautical Society*, February, pp. 127–150.
- Lefebvre, A. H. (1965). A method of predicting the aerodynamic blockage of bluff bodies in a ducted airstream. CoA Report AERO No. 188, November.
- NACA RM E55G28 (1955). *Adaptation of Combustion Principles to Aircraft Propulsion*, Vol. II—Combustion in Air Breathing Jet Engines.
