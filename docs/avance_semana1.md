# Avance Semana 1 — SIMTELE-RISK
## Plataforma de Simulación Numérica y Análisis de Riesgos (Contexto: *Mi Teleférico*, La Paz)

> **Nota Académica:** Todos los modelos, parámetros físicos y series de datos son estrictamente sintéticos con fines educativos y no representan fallas ni mediciones reales de operación.

---

## 1. Planteamiento Formal de los 4 Modelos Matemáticos

### Módulo 1: Detención de Emergencia de Cabinas (`MOD1_DETENCION`)
* **Variables y Unidades:**
  * $t$: tiempo transcurrido desde la activación del freno $[\text{s}]$
  * $x(t)$: distancia recorrida por la cabina $[\text{m}]$
  * $v(t)$: velocidad lineal de la cabina $[\text{m/s}]$
  * $a_0$: desaceleración nominal de frenado $[\text{m/s}^2]$, $k_d$: coeficiente de arrastre/pendiente $[\text{s}^{-1}]$
* **Sistema de Ecuaciones (EDO de primer orden):**
  $$\frac{dx}{dt} = v(t), \qquad \frac{dv}{dt} = -a(v,t) = -(a_0 + k_d v(t))$$
* **Condiciones Iniciales:** $x(0) = x_0 = 0\text{ m}$, $v(0) = v_0 > 0\text{ m/s}$.
* **Hipótesis:** Movimiento unidimensional sobre el cable portador-tractor; masa efectiva constante durante el frenado; sin deslizamiento de pinza.
* **Solución Analítica de Referencia ($k_d = 0$):**
  $$v(t) = v_0 - a_0 t, \quad t_{\text{det}} = \frac{v_0}{a_0}, \quad x_{\text{det}} = \frac{v_0^2}{2a_0}$$
* **Escenarios ($1 \times 3$):**
  * **NORMAL:** Frenado nominal en tramo recto ($v_0 = 6.0\text{ m/s}$, $a_0 = 1.2\text{ m/s}^2$, $k_d = 0$, $h = 0.05\text{ s}$).
  * **ESTRÉS:** Carga máxima con paso grueso ($v_0 = 8.5\text{ m/s}$, $a_0 = 0.75\text{ m/s}^2$, $k_d = 0.02\text{ s}^{-1}$, $h = 0.4\text{ s}$).
  * **MAL CONDICIONADO:** Frenado asintótico con raíz múltiple ($v(t_{\text{det}}) = 0$ y $v'(t_{\text{det}}) = 0$), degradando la convergencia cuadrática de Newton-Raphson.

---

### Módulo 2: Deterioro Mecánico y Mantenimiento (`MOD2_DETERIORO`) — *Implementado en Semana 1*
* **Variables y Unidades:**
  * $\mathbf{x} \in \mathbb{R}^n$: vector de parámetros calibrados de rigidez/desgaste por tramo $[\text{adimensional / mm}\cdot\text{mes}^{-1}]$
  * $A \in \mathbb{R}^{n \times n}$: matriz Simétrica Definida Positiva (SPD) de acoplamiento estructural
  * $\mathbf{b} \in \mathbb{R}^n$: vector de esfuerzos/lecturas de inspección acumuladas
  * $D(t)$: índice de desgaste normalizado $[0, 1]$, con umbral crítico $D_{\text{umbral}} \in (0, 1)$
* **Ecuaciones:**
  1. Calibración de parámetros: $A\mathbf{x} = \mathbf{b}$
  2. Evolución temporal del desgaste: $D(t) = D_0 + \alpha t + \beta t^2$, buscando $t^*$ tal que $D(t^*) - D_{\text{umbral}} = 0$.
* **Condiciones Iniciales e Hipótesis:** $D(0) = D_0 < D_{\text{umbral}}$; $\alpha, \beta > 0$; matriz $A = A^T$ con $\lambda_{\min}(A) > 0$ (SPD) en calibración física válida.
* **Escenarios ($1 \times 3$):**
  * **NORMAL:** Matriz SPD diagonalmente dominante $n=4$, $\kappa_2(A) < 10$, $\text{tol} = 10^{-8}$.
  * **ESTRÉS:** Sistema SPD ampliado $n=12$, tolerancia estricta $\text{tol} = 10^{-11}$, $\text{max\_iter} = 2000$.
  * **MAL CONDICIONADO:** Matriz SPD tipo Hilbert perturbada $n=6$ ($\kappa_2(A) > 10^5$) sometida a perturbación $\frac{\|\delta \mathbf{b}\|_2}{\|\mathbf{b}\|_2} = 10^{-4}$.

---

### Módulo 3: Oscilaciones por Viento (`MOD3_OSCILACIONES`)
* **Variables y Unidades:**
  * $x(t)$: desplazamiento lateral de cabina $[\text{m}]$, $\dot{x}(t)$: velocidad lateral $[\text{m/s}]$
  * $m$: masa efectiva $[\text{kg}]$, $c$: amortiguamiento $[\text{N}\cdot\text{s/m}]$, $k$: rigidez equivalente $[\text{N/m}]$
  * $F(t) = F_0 \sin(\omega t)$: fuerza aerodinámica de ráfaga $[\text{N}]$
* **Ecuación Diferencial (2.º orden reducida a sistema $2 \times 2$):**
  $$m\ddot{x} + c\dot{x} + kx = F(t) \quad \Longleftrightarrow \quad \begin{cases} \dot{x} = v \\ \dot{v} = \frac{1}{m}(F(t) - cv - kx) \end{cases}$$
* **Condiciones Iniciales e Hipótesis:** $x(0) = x_0$, $v(0) = v_0$; régimen lineal elástico; energía acumulada proporcional a $\int_0^T x(t)^2\,dt$.
* **Solución Analítica de Referencia ($F(t)=0$, subamortiguado $\zeta < 1$):**
  $$x(t) = e^{-\zeta\omega_0 t}\left[C_1 \cos(\omega_d t) + C_2 \sin(\omega_d t)\right], \quad \omega_0 = \sqrt{\frac{k}{m}}, \quad \zeta = \frac{c}{2\sqrt{mk}}$$
* **Escenarios ($1 \times 3$):**
  * **NORMAL:** Brisa moderada subamortiguada ($m=1200$, $c=480$, $k=3000$, $h=0.02\text{ s}$, $T=20\text{ s}$).
  * **ESTRÉS:** Forzamiento cercano a resonancia ($\omega = 1.55\text{ rad/s}$, $F_0 = 850\text{ N}$, $T=120\text{ s}$).
  * **MAL CONDICIONADO:** Sistema rígido (*stiff*) con alta rigidez ($k=450000\text{ N/m}$) y paso explícito crítico ($h=0.12\text{ s}$).

---

### Módulo 4: Reconstrucción de Señales de Sensores (`MOD4_SENSORES`)
* **Variables y Unidades:**
  * $t_i \in [a, b]$: instantes de muestreo $[\text{s}]$, $y_i = y(t_i) + \eta_i$: telemetría con ruido $\eta_i \sim \mathcal{N}(0, \sigma^2)$
  * $P(t)$: polinomio interpolante o spline cúbico natural que reconstruye nodos ocultos $t_j \in \mathcal{O}$
* **Ecuaciones:** Reconstrucción $P(t_j) \approx y(t_j)$ y detección de cruce de umbral $P(t^*) - y_{\text{umbral}} = 0$.
* **Hipótesis:** Señal continua en $[a, b]$ con pérdida discreta de paquetes en índices ocultos.
* **Escenarios ($1 \times 3$):**
  * **NORMAL:** Señal limpia $y(t) = \sin(t)$ en $[0, 2\pi]$ con 8 nodos equiespaciados y 2 ocultos.
  * **ESTRÉS:** Señal amortiguada $y(t) = e^{-t}\cos(2t)$ en $[0, 5]$ con ruido $\sigma = 0.04$ y 4 nodos ocultos.
  * **MAL CONDICIONADO:** Función de Runge $f(t) = \frac{1}{1 + 25t^2}$ en $[-5, 5]$ con 15 nodos equiespaciados (oscilación polinomial en extremos).

---

## 2. Ejemplo Numérico Resuelto Paso a Paso (Jacobi y Gauss-Seidel)

Consideramos el sistema $4 \times 4$ del escenario **NORMAL** del Módulo 2:
$$A = \begin{pmatrix} 10 & -1.5 & 0 & 0 \\ -1.5 & 10 & -1.5 & 0 \\ 0 & -1.5 & 10 & -1.5 \\ 0 & 0 & -1.5 & 10 \end{pmatrix}, \qquad \mathbf{b} = \begin{pmatrix} 10.725 \\ 5.875 \\ 3.775 \\ 2.175 \end{pmatrix}, \qquad \mathbf{x}^* = \begin{pmatrix} 1.20 \\ 0.85 \\ 0.55 \\ 0.30 \end{pmatrix}$$
Partiendo del vector inicial $\mathbf{x}^{(0)} = [0,\; 0,\; 0,\; 0]^T$:

### Método de Jacobi
Fórmula de actualización: $x_i^{(k+1)} = \frac{1}{a_{ii}}\left(b_i - \sum_{j \ne i} a_{ij} x_j^{(k)}\right)$.

* **Iteración $k = 1$:**
  * $x_1^{(1)} = \frac{10.725}{10} = 1.072500$
  * $x_2^{(1)} = \frac{5.875}{10} = 0.587500$
  * $x_3^{(1)} = \frac{3.775}{10} = 0.377500$
  * $x_4^{(1)} = \frac{2.175}{10} = 0.217500$
* **Iteración $k = 2$:**
  * $x_1^{(2)} = \frac{10.725 + 1.5(0.5875)}{10} = 1.160625$
  * $x_2^{(2)} = \frac{5.875 + 1.5(1.0725 + 0.3775)}{10} = 0.805000$
  * $x_3^{(2)} = \frac{3.775 + 1.5(0.5875 + 0.2175)}{10} = 0.498250$
  * $x_4^{(2)} = \frac{2.175 + 1.5(0.3775)}{10} = 0.274125$

### Método de Gauss-Seidel
Fórmula de actualización secuencial: $x_i^{(k+1)} = \frac{1}{a_{ii}}\left(b_i - \sum_{j < i} a_{ij} x_j^{(k+1)} - \sum_{j > i} a_{ij} x_j^{(k)}\right)$.

* **Iteración $k = 1$:**
  * $x_1^{(1)} = \frac{10.725}{10} = 1.072500$
  * $x_2^{(1)} = \frac{5.875 + 1.5(1.0725)}{10} = 0.748375$
  * $x_3^{(1)} = \frac{3.775 + 1.5(0.748375)}{10} = 0.489756$
  * $x_4^{(1)} = \frac{2.175 + 1.5(0.48975625)}{10} = 0.290963$
* **Iteración $k = 2$:**
  * $x_1^{(2)} = \frac{10.725 + 1.5(0.748375)}{10} = 1.184756$
  * $x_2^{(2)} = \frac{5.875 + 1.5(1.18475625 + 0.48975625)}{10} = 0.838677$
  * $x_3^{(2)} = \frac{3.775 + 1.5(0.83867688 + 0.29096344)}{10} = 0.546946$
  * $x_4^{(2)} = \frac{2.175 + 1.5(0.54694605)}{10} = 0.299542$

Se observa cómo en solo 2 iteraciones Gauss-Seidel ($\mathbf{x}^{(2)} \approx [1.185, 0.839, 0.547, 0.300]^T$) se aproxima más rápido a $\mathbf{x}^*$ que Jacobi ($\mathbf{x}^{(2)} \approx [1.161, 0.805, 0.498, 0.274]^T$).

---

## 3. Resultados y Errores Generados por el Código (Módulo 2)

Ejecución directa de `python -m app.modules.modulo2_s1` en precisión `float64`:

### Escenario 1: `NORMAL` ($n=4$, $\text{tol}=10^{-8}$, $\kappa_2(A)=1.6410$, Amplificación $\delta \mathbf{b}=0.80\times$)

| Método | Convergió | Iteraciones | Tiempo (ms) | Residual $\|\mathbf{b}-A\mathbf{x}\|_2$ | Error Relativo $E_{rel}$ | Error % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Jacobi | Sí | 15 | 0.7773 | $6.434 \times 10^{-9}$ | $5.262 \times 10^{-10}$ | $5.262 \times 10^{-8}\%$ |
| Gauss-Seidel | Sí | 9 | 0.5429 | $7.430 \times 10^{-10}$ | $5.174 \times 10^{-11}$ | $5.174 \times 10^{-9}\%$ |
| Factorización LU (Pivoteo Parcial) | Sí | 1 | 0.0962 | $1.776 \times 10^{-15}$ | $0.000 \times 10^{0}$ | $0.000\%$ |
| Gradiente Conjugado (CG) | Sí | 4 | 0.2258 | $3.972 \times 10^{-15}$ | $1.701 \times 10^{-16}$ | $1.701 \times 10^{-14}\%$ |

### Escenario 2: `ESTRES` ($n=12$, $\text{tol}=10^{-11}$, $\kappa_2(A)=2.0764$, Amplificación $\delta \mathbf{b}=0.68\times$)

| Método | Convergió | Iteraciones | Tiempo (ms) | Residual $\|\mathbf{b}-A\mathbf{x}\|_2$ | Error Relativo $E_{rel}$ | Error % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Jacobi | Sí | 31 | 1.1609 | $4.501 \times 10^{-12}$ | $3.561 \times 10^{-13}$ | $3.561 \times 10^{-11}\%$ |
| Gauss-Seidel | Sí | 18 | 0.8615 | $4.878 \times 10^{-12}$ | $3.252 \times 10^{-13}$ | $3.252 \times 10^{-11}\%$ |
| Factorización LU (Pivoteo Parcial) | Sí | 1 | 0.1711 | $1.538 \times 10^{-15}$ | $7.090 \times 10^{-17}$ | $7.090 \times 10^{-15}\%$ |
| Gradiente Conjugado (CG) | Sí | 12 | 0.3384 | $3.408 \times 10^{-14}$ | $1.307 \times 10^{-15}$ | $1.307 \times 10^{-13}\%$ |

### Escenario 3: `MAL_CONDICIONADO` ($n=6$ Hilbert perturbada, $\text{tol}=10^{-8}$, $\kappa_2(A)=1.4937 \times 10^7$, Amplificación $\delta \mathbf{b}=7\,031\,425.91\times$)

| Método | Convergió | Iteraciones | Tiempo (ms) | Residual $\|\mathbf{b}-A\mathbf{x}\|_2$ | Error Relativo $E_{rel}$ | Error % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Jacobi | No | 158 | 4.1100 | $3.514 \times 10^{100}$ | $2.135 \times 10^{100}$ | Divergió |
| Gauss-Seidel | No | 5000 | 147.2676 | $1.263 \times 10^{-7}$ | $5.218 \times 10^{-3}$ | $5.218 \times 10^{-1}\%$ |
| Factorización LU (Pivoteo Parcial) | Sí | 1 | 0.1662 | $2.544 \times 10^{-16}$ | $1.677 \times 10^{-10}$ | $1.677 \times 10^{-8}\%$ |
| Gradiente Conjugado (CG) | Sí | 6 | 0.2291 | $1.452 \times 10^{-10}$ | $8.619 \times 10^{-4}$ | $8.619 \times 10^{-2}\%$ |

**Conclusión de Condicionamiento vs. Convergencia:**
En el escenario `MAL_CONDICIONADO`, Jacobi falla por **divergencia iterativa** ($\rho(T_J) > 1$ al no ser diagonalmente dominante), mientras que LU y CG alcanzan residuales pequeños ($10^{-16}$ y $10^{-10}$). Sin embargo, debido a $\kappa_2(A) \approx 1.49 \times 10^7$, un residual de $1.45 \times 10^{-10}$ en CG aún deja un error relativo en la solución de $8.62 \times 10^{-4}$, y una perturbación de $10^{-4}$ en $\mathbf{b}$ se amplifica en más de **$7 \times 10^6$ veces** en $\mathbf{x}$.
