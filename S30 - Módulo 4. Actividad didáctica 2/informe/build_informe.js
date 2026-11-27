// Genera el informe .docx a partir de los CSV de ../data (todas las cifras salen de ahí).
// Uso (desde la carpeta informe):  npm install  &&  node build_informe.js
const fs = require("fs");
const path = require("path");
const { ExternalHyperlink, TableOfContents } = require("docx");
const { P, H1, H2, BUL, EQ, CAP_TOP, CODE, TABLE, FIG, buildDocument, Packer, Paragraph, TextRun, AlignmentType } = require("./lib");

const ROOT = path.resolve(__dirname, "..");
const DATA = path.join(ROOT, "data");
const FIGS = path.join(ROOT, "figures");
const AUTOR = "Santiago Andrés Valencia Duque";
const AFILIACION = "Ingeniería de Software y Datos, IU Digital de Antioquia";
const REPO = "https://github.com/andresvd95/Simulacion/tree/main/S30%20-%20M%C3%B3dulo%204.%20Actividad%20did%C3%A1ctica%202";
const VIDEO = "https://drive.google.com/file/d/1IW0_flvvKN5enuMaS3RsAGetLLPkthR8/view?usp=sharing";
const VIDEO_GH = REPO.replace("/tree/", "/blob/") + "/video/sustentacion_actividad4.mp4";
const SALIDA = "Valencia_Santiago_problemaParqueadero.docx";
const FONT = "Times New Roman";
const enlace = (texto, url) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [
  new TextRun({ text: texto, size: 20, font: FONT }),
  new ExternalHyperlink({ link: url, children: [new TextRun({ text: decodeURI(url), style: "Hyperlink", size: 20, font: FONT, color: "0563C1", underline: {} })] })] });

// ---------- datos (lector de CSV que respeta comillas)
function parseLine(line) {
  const out = [];
  let cur = "", q = false;
  for (const ch of line) {
    if (ch === '"') q = !q;
    else if (ch === "," && !q) { out.push(cur); cur = ""; }
    else cur += ch;
  }
  out.push(cur);
  return out;
}
function readCsv(file) {
  const [head, ...rows] = fs.readFileSync(path.join(DATA, file), "utf8").trim().split(/\r?\n/);
  const cols = parseLine(head);
  return rows.map((r) => {
    const v = parseLine(r);
    const o = {};
    cols.forEach((c, i) => (o[c] = v[i] !== "" && !isNaN(Number(v[i])) ? Number(v[i]) : v[i]));
    return o;
  });
}
const kv = (file) => Object.fromEntries(readCsv(file).map((r) => [Object.values(r)[0], Object.values(r)[1]]));
const EE = kv("estado_estable.csv");
const ad = readCsv("antes_despues.csv");
const rc = readCsv("resumen_cajero.csv");
const tcaj = readCsv("usuarios_tipo_cajero.csv");
const trep = readCsv("usuarios_tipo_replica.csv");
const ptipo = readCsv("por_tipo.csv");
const dec = readCsv("decision.csv");
const comp = readCsv("comparaciones.csv");
const sens = readCsv("sensibilidad.csv");
const calib = readCsv("calibracion.csv");
const val = kv("validacion.csv");
const anova = kv("anova_cajeros.csv");
const env = fs.readFileSync(path.join(DATA, "entorno.txt"), "utf8").trim().split(/\r?\n/);

const n = (x, d = 2) => Number(x).toFixed(d).replace(".", ",");
const pc = (x, d = 1) => n(100 * x, d) + " %";
const pv = (p) => (p < 0.001 ? "< 0,001" : "= " + n(p, 2));
const ci = (r, d = 2) => `${n(r.media, d)} [${n(r.ic_inf, d)}; ${n(r.ic_sup, d)}]`;
const RC = (e, k, m) => rc.find((r) => r.escenario === e && r.cajero === k && r.metrica === m);
const D = (e) => dec.find((r) => r.escenario === e);
const CMP = (a, b) => comp.find((r) => r.a === a && r.b === b);
const AD = (k) => ad.find((r) => r.indicador === k);
const SI = (x) => x === true || x === "True";

const TIPOS = ["Rápido", "Normal", "Lento", "Muy lento"];
const TABLA = { "Rápido": [1, 3, 0.25], "Normal": [3, 3, 0.2], "Lento": [4, 5, 0.275], "Muy lento": [6, 7, 0.275] };
const ESC = ["S0_3_filas", "S1_4_filas", "S2_5_filas", "S3_3_fila_unica", "S4_4_fila_unica"];
const NOM = Object.fromEntries(dec.map((r) => [r.escenario, r.descripcion]));
const CORTO = { S0_3_filas: "S0", S1_4_filas: "S1", S2_5_filas: "S2", S3_3_fila_unica: "S3", S4_4_fila_unica: "S4" };
const N = EE.replicas_usadas, TW = EE.t_transitorio_min, NIVEL = EE.nivel_estable_min;
const META_W = 5, META_P = 0.1;

// ---------- cálculos derivados
const EA = TIPOS.reduce((s, t) => s + TABLA[t][2] * TABLA[t][1], 0);   // media entre llegadas de un flujo
const tuso = [1, 2, 3].map((k) => ({ k, r: RC("S0_3_filas", k, "t_uso") }));
const tmax = tuso.reduce((a, b) => (b.r.media > a.r.media ? b : a));
const tmin = tuso.reduce((a, b) => (b.r.media < a.r.media ? b : a));
const tmed = tuso.find((x) => x.k !== tmax.k && x.k !== tmin.k);
const mediana = (xs) => { const s = [...xs].sort((a, b) => a - b); const m = s.length / 2; return s.length % 2 ? s[Math.floor(m)] : (s[m - 1] + s[m]) / 2; };
const moda = (xs) => { const c = {}; xs.forEach((x) => (c[x] = (c[x] || 0) + 1)); const mx = Math.max(...Object.values(c)); return Object.keys(c).filter((k) => c[k] === mx).map(Number); };
const desv = (xs) => { const m = xs.reduce((a, b) => a + b, 0) / xs.length; return Math.sqrt(xs.reduce((s, x) => s + (x - m) ** 2, 0) / (xs.length - 1)); };
const tend = [...TIPOS, "Total"].map((t) => {
  const xs = trep.map((r) => r[t]);
  return { t, media: xs.reduce((a, b) => a + b, 0) / xs.length, med: mediana(xs), moda: moda(xs), de: desv(xs), min: Math.min(...xs), max: Math.max(...xs) };
});
const TOT = tend.find((x) => x.t === "Total");
const cajTot = tcaj.filter((r) => r.cajero !== "Total");
const rho = val["ρ por cajero, teórico"];
const subest = 1 - AD("espera_min").con_transitorio / AD("espera_min").sin_transitorio;
const escSens = [...new Set(sens.map((r) => r.escenario))];
const repSens = [...new Set(sens.map((r) => r.reparto))];

// ---------- documento
const C_ = [];
const push = (...xs) => xs.flat().forEach((x) => C_.push(x));
const titulo = (t, size = 32, bold = true, after = 120) =>
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after }, children: [new TextRun({ text: t, bold, size, font: FONT })] });

push(
  new Paragraph({ spacing: { before: 2400 }, children: [] }),
  titulo("Solución de un problema de parqueaderos", 32),
  titulo("Estado estable, número de corridas y capacidad de los cajeros de pago del Supercentro", 26, false, 600),
  titulo("Módulo 4, Actividad didáctica 2, Simulación", 22, false),
  titulo(AUTOR, 22, true),
  titulo(AFILIACION, 22, false),
  titulo("Noviembre de 2026", 22, false, 400),
  enlace("Video de sustentación (Drive): ", VIDEO),
  enlace("Video en GitHub: ", VIDEO_GH),
  enlace("Repositorio: ", REPO),
  new Paragraph({ pageBreakBefore: true, spacing: { after: 200 }, children: [new TextRun({ text: "Índice", bold: true, size: 24, font: FONT })] }),
  new TableOfContents("Índice", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ pageBreakBefore: true, children: [] }),
);

// 1. Introducción
push(
  H1("1. Introducción"),
  P("El centro comercial Supercentro tiene, en cada punto de salida del parqueadero, cajeros de autopago donde los usuarios pagan el tiempo de parqueo. Hoy hay 3 cajeros por punto. Cada cajero tiene su propia fila; el usuario escoge una y no se cambia de fila ni abandona el sistema, de modo que cada cajero se comporta como una cola M/M/1 independiente. Los usuarios son de cuatro tipos (rápido, normal, lento y muy lento) que difieren en el tiempo medio que tardan en usar el cajero y en el tiempo medio entre sus llegadas. La administración quiere saber si 3 cajeros bastan o si debe instalar más."),
  P("Como el parqueadero opera de forma continua durante toda la jornada, la pregunta se refiere al comportamiento del sistema en **estado estable**, no al arranque con las filas vacías. Por eso el trabajo empieza identificando el periodo transitorio con la técnica de la media sobre una variable (método de Welch) y definiendo el número de corridas con la media acumulada sobre las réplicas. Después se elimina el transitorio y, con los datos del estado estable, se responden los puntos del enunciado: (1) el cajero con el menor y el mayor tiempo promedio de atención; (2) el promedio de usuarios de cada tipo en el total de cajeros; (3) una estrategia de mejora con su criterio de decisión; (4) los procesos de verificación, calibración y validación, y (5) el algoritmo de eliminación del transitorio con las gráficas antes y después."),
);

// 2. Metodología
push(
  H1("2. Metodología"),
  H2("2.1 Datos de entrada"),
  P("La Tabla 1 resume los parámetros del enunciado. Ambos tiempos son exponenciales. El enunciado fija el 25 % de usuarios rápidos y el 20 % de normales, y dice que el resto son lentos o muy lentos sin separarlos; se supuso un reparto igual (27,5 % cada uno) y en la Sección 3.3 se analiza qué pasa si ese reparto cambia."),
  CAP_TOP("Tabla 1. Parámetros por tipo de usuario (tiempos en minutos)"),
  TABLE(["Tipo de usuario", "Media de uso del cajero", "Media entre llegadas", "Proporción"],
    TIPOS.map((t) => [t, n(TABLA[t][0], 0), n(TABLA[t][1], 0), pc(TABLA[t][2])]), [2700, 2300, 2300, 2060]),
  H2("2.2 Modelo conceptual y supuestos"),
  P("Cada uno de los 3 cajeros actuales recibe un flujo de usuarios. En cada flujo se sortea el tipo del siguiente usuario con las proporciones de la Tabla 1; con ese tipo se generan el tiempo hasta su llegada (exponencial con la media de llegada del tipo) y su tiempo de uso del cajero (exponencial con la media de uso). La demanda total es la suma de los tres flujos. Al llegar, el usuario escoge una fila al azar y espera su turno en orden de llegada (FIFO)."),
  ...BUL([
    "Cada cajero es una cola con un servidor, fila propia y disciplina FIFO; no hay cambio de fila ni deserción, como indica el enunciado.",
    "La jornada simulada dura 12 horas (720 min), un horario típico de un centro comercial; quien llega antes del cierre es atendido.",
    "El sistema arranca vacío. Ese arranque no representa la operación normal del parqueadero, por lo que se identifica y se descarta el periodo transitorio (Secciones 2.5 y 3.5).",
    "La demanda es la misma en todos los escenarios (números aleatorios comunes [1], [2]): la réplica r usa la semilla r, así que los escenarios se comparan con exactamente los mismos usuarios.",
  ]),
  P(`Con estos datos, el tiempo medio entre llegadas de un flujo es ${n(EA)} min, la tasa de llegadas a cada cajero es λ = ${n(1 / EA, 3)} usuarios/min (unos ${n(val["Usuarios por día, teórico"], 0)} usuarios por día en total) y el uso medio es E[S] = ${n(val["Uso medio del cajero, teórico (min)"])} min. La ocupación teórica de cada cajero es ρ = λ·E[S] = ${n(rho, 3)}: el sistema es estable (ρ < 1), pero está cargado, y en esa zona la fila crece mucho con pequeñas variaciones de la demanda.`),
  H2("2.3 Escenarios"),
  P("Se compararon cinco configuraciones (Tabla 2). S0 es la situación actual. S1 y S2 agregan cajeros con filas independientes. S3 y S4 cambian la organización: una sola fila que alimenta a todos los cajeros, de modo que el primero de la fila pasa al primer cajero que se libere."),
  CAP_TOP("Tabla 2. Escenarios simulados"),
  TABLE(["Escenario", "Cajeros", "Organización de la fila"],
    ESC.map((e) => [CORTO[e] + (e === "S0_3_filas" ? " (actual)" : ""), String(D(e).cajeros), SI(D(e).fila_unica) ? "Una fila única" : "Una fila por cajero"]), [3000, 2000, 4360]),
  H2("2.4 Implementación"),
  P("El modelo se programó en Python con la librería de simulación de eventos discretos SimPy [5]; NumPy [6] genera los números aleatorios, SciPy [7] calcula intervalos de confianza y pruebas, y Matplotlib [8] produce las gráficas. Cada cajero con fila propia es un recurso SimPy de capacidad 1; la fila única se modela con un almacén (Store) de cajeros libres. Entorno: " + env.join(", ") + "."),
  H2("2.5 Estado estable: técnica de la media sobre una variable (Welch)"),
  P(`La variable de salida elegida es el **tiempo de espera en cola**. Se hizo una corrida piloto de ${EE.r_piloto} réplicas del escenario actual. La jornada se dividió en intervalos de ${EE.intervalo_min} minutos y, para cada intervalo, se calculó la espera media de los usuarios que llegaron en él, promediando sobre las ${EE.r_piloto} réplicas. Esa curva todavía es ruidosa, así que se suavizó con una media móvil centrada de ${2 * EE.ventana_welch + 1} puntos, según el método de Welch [1], [3]:`),
  EQ(`Ȳ_{i}(w) = (1 / (2w + 1)) · Σ_{s = −w..w} Ȳ_{i+s},   con w = ${EE.ventana_welch}`),
  P(`La Figura 1 muestra el resultado. La espera parte de casi cero (las filas están vacías al abrir), sube durante las primeras horas y luego oscila alrededor de un nivel constante. Para no depender de una lectura a ojo, el fin del transitorio se determinó con un algoritmo: el nivel estable es la media de la segunda mitad de la curva suavizada (${n(NIVEL)} min) y el transitorio termina en el primer intervalo donde la media móvil alcanza el ${pc(1 - EE.tol_transitorio, 0)} de ese nivel. Así se obtuvo un **fin del transitorio de ${n(TW, 0)} minutos**.`),
  ...FIG(path.join(FIGS, "fig1_welch.png"), 6.3, `Figura 1. Método de Welch: espera media por intervalo de 10 min (${EE.r_piloto} réplicas) y su media móvil. La zona gris es el transitorio.`),
  H2("2.6 Número de corridas: media acumulada sobre las réplicas"),
  P("Para definir cuántas corridas hacen falta se calculó la espera media de cada réplica piloto, ya sin el transitorio, y su media acumulada a medida que se agregan réplicas (Figura 2). Al principio la media acumulada salta mucho, porque cada réplica nueva pesa bastante; con más réplicas se estabiliza. Se tomó como criterio que la media acumulada quede dentro de ±5 % de su valor final a partir de cierto n, y se contrastó con la fórmula clásica del intervalo de confianza [1], [2]:"),
  EQ("t_{0,975; n−1} · s / √n ≤ ε · x̄"),
  P(`donde s y x̄ son la desviación estándar y la media de la corrida piloto, y ε = ${pc(EE.precision_ic, 0)} es el semiancho relativo aceptado. La media acumulada se estabiliza desde **n = ${EE.n_media_acumulada}** y la fórmula pide **n = ${EE.n_formula_ic}**. Se tomó el mayor de los dos: **${N} réplicas por escenario**. La gran variabilidad entre días (la espera media de una réplica va de unos 6 a más de 30 minutos) explica que hagan falta tantas corridas.`),
  ...FIG(path.join(FIGS, "fig2_media_acumulada.png"), 6.3, "Figura 2. Media acumulada de la espera sobre las réplicas, con y sin transitorio. La banda marca ±5 % del valor final."),
  CAP_TOP("Tabla 3. Parámetros del análisis de estado estable"),
  TABLE(["Parámetro", "Valor"], [
    ["Réplicas piloto", String(EE.r_piloto)], ["Intervalo de agrupación", `${EE.intervalo_min} min`],
    ["Ventana de la media móvil", `${2 * EE.ventana_welch + 1} intervalos`], ["Nivel estable de la espera", `${n(NIVEL)} min`],
    ["Fin del transitorio", `${n(TW, 0)} min`], ["n por media acumulada (±5 %)", String(EE.n_media_acumulada)],
    ["n por fórmula del IC 95 % (±10 %)", String(EE.n_formula_ic)], ["Réplicas usadas por escenario", String(N)]], [6000, 3360]),
);

// 3. Resultados
push(
  H1("3. Resultados"),
  P(`Todos los resultados de esta sección provienen de ${N} réplicas por escenario, descartando los usuarios que llegaron durante los primeros ${n(TW, 0)} minutos. Las cifras se reportan como media con intervalo de confianza del 95 %.`),
  H2("3.1 Punto 1: cajero con menor y mayor tiempo promedio de atención"),
  CAP_TOP(`Tabla 4. Indicadores por cajero en la situación actual, media [IC 95 %], ${N} réplicas`),
  TABLE(["Cajero", "Atención (min)", "Espera en cola (min)", "Usuarios atendidos", "Utilización"],
    [1, 2, 3].map((k) => [`Cajero ${k}`, ci(RC("S0_3_filas", k, "t_uso")), ci(RC("S0_3_filas", k, "espera")), ci(RC("S0_3_filas", k, "usuarios"), 1), ci(RC("S0_3_filas", k, "utilizacion"), 3)]),
    [1300, 2000, 2100, 2060, 1900]),
  ...FIG(path.join(FIGS, "fig4_tiempo_cajero.png"), 5.2, "Figura 3. Tiempo promedio de atención por cajero (situación actual)."),
  P(`El cajero con el **menor** tiempo promedio de atención es el **cajero ${tmin.k}** (${n(tmin.r.media)} min) y el de **mayor** es el **cajero ${tmax.k}** (${n(tmax.r.media, 4)} min), seguido muy de cerca por el cajero ${tmed.k} (${n(tmed.r.media, 4)} min). La diferencia es de ${n(tmax.r.media - tmin.r.media)} min y no es estadísticamente significativa: un ANOVA de un factor sobre las ${N} réplicas da F = ${n(anova.F)} y p ${pv(anova.p)}. Era lo esperado: los cajeros son idénticos y cada uno recibe la misma mezcla de usuarios, así que el tiempo de atención depende de qué tipos de usuario le tocan, no del cajero. Sí hay diferencias de un día a otro (desviación estándar de unos ${n(tmin.r.de, 2)} min entre réplicas), que son las que hacen variar las filas.`),

  H2("3.2 Punto 2: promedio de usuarios de cada tipo en el total de cajeros"),
  P(`La Tabla 5 muestra cuántos usuarios de cada tipo atiende cada cajero en promedio durante el periodo estable de una réplica (${n(720 - TW, 0)} minutos) y el total de los tres cajeros. La Tabla 6 resume las medidas de tendencia central del total de cada tipo sobre las ${N} réplicas.`),
  CAP_TOP(`Tabla 5. Usuarios promedio por réplica según tipo y cajero (estado estable, ${N} réplicas)`),
  TABLE(["Cajero", ...TIPOS, "Total"],
    [...cajTot.map((r) => [`Cajero ${r.cajero}`, ...TIPOS.map((t) => n(r[t], 1)), n(r.Total, 1)]),
     ["**Total cajeros**", ...TIPOS.map((t) => `**${n(tcaj.find((r) => r.cajero === "Total")[t], 1)}**`), `**${n(tcaj.find((r) => r.cajero === "Total").Total, 1)}**`]],
    [2160, 1440, 1440, 1440, 1440, 1440]),
  CAP_TOP("Tabla 6. Medidas de tendencia central y dispersión del número de usuarios por tipo (total de cajeros, por réplica)"),
  TABLE(["Tipo", "Media", "Mediana", "Moda", "Desv. estándar", "Mínimo", "Máximo", "% del total"],
    tend.map((x) => [x.t, n(x.media, 1), n(x.med, 1), x.moda.slice(0, 2).join(", "), n(x.de, 1), String(x.min), String(x.max), x.t === "Total" ? "100 %" : pc(x.media / TOT.media)]),
    [1300, 1000, 1100, 1100, 1300, 1100, 1100, 1360]),
  ...FIG(path.join(FIGS, "fig5_usuarios_tipo.png"), 6.0, "Figura 4. Promedio de usuarios de cada tipo por cajero (estado estable)."),
  P(`En el periodo estable se atienden en promedio ${n(TOT.media, 1)} usuarios por réplica entre los tres cajeros, unos ${n(TOT.media / 3, 1)} por cajero. Los tipos más frecuentes son lento (${n(tend[2].media, 1)}) y muy lento (${n(tend[3].media, 1)}), y el menos frecuente es normal (${n(tend[1].media, 1)}). La media y la mediana casi coinciden en todos los tipos, señal de que el número de usuarios por réplica se distribuye de forma simétrica. Las proporciones observadas (${TIPOS.map((t, i) => `${t.toLowerCase()} ${pc(tend[i].media / TOT.media)}`).join(", ")}) concuerdan con las de la Tabla 1, y los tres cajeros reciben cantidades y mezclas parecidas porque los usuarios eligen la fila al azar.`),
  P(`Un detalle útil para la decisión es que todos los tipos esperan casi lo mismo en la fila (de ${n(Math.min(...ptipo.map((r) => r.espera)), 1)} a ${n(Math.max(...ptipo.map((r) => r.espera)), 1)} min en la situación actual): un usuario rápido, que usa el cajero apenas 1 minuto, puede pasar 15 minutos esperando detrás de usuarios lentos. Esa es la principal fuente de insatisfacción del sistema actual.`),

  H2("3.3 Punto 3: estrategia de mejora y criterio de decisión"),
  P(`**Criterio de decisión.** Para que el grupo de trabajo decida con una regla clara y verificable, se definió que una configuración es aceptable si cumple dos condiciones de servicio a la vez: (a) la espera promedio en cola es de **${META_W} minutos o menos**, y (b) **como máximo el ${pc(META_P, 0)} de los usuarios espera más de 10 minutos**. La segunda condición protege a los usuarios que caen en los días o en los momentos más congestionados, que el promedio esconde. Entre las configuraciones aceptables se escoge la de **menor número de cajeros** (menor inversión); si ninguna con 3 cajeros cumple, se justifica instalar más.`),
  CAP_TOP(`Tabla 7. Resultados por escenario (estado estable, ${N} réplicas)`),
  TABLE(["Escenario", "Espera media (min) [IC 95 %]", "% espera > 10 min", "Percentil 95 (min)", "Utilización", "¿Cumple?"],
    ESC.map((e) => { const r = D(e); return [`${CORTO[e]}: ${NOM[e]}`, `${n(r.espera)} [${n(r.ic_inf)}; ${n(r.ic_sup)}]`, pc(r.p_espera_10), n(r.espera_p95, 1), n(r.utilizacion, 2), SI(r.cumple) ? "**Sí**" : "No"]; }),
    [2900, 1900, 1200, 1200, 1060, 1100]),
  ...FIG(path.join(FIGS, "fig6_escenarios.png"), 6.4, "Figura 5. Espera promedio y porcentaje de usuarios que esperan más de 10 min. Las líneas punteadas son los límites del criterio; en verde, la configuración que cumple."),
  P(`**Los 3 cajeros actuales no son suficientes.** En la situación actual la espera promedio es de ${n(D("S0_3_filas").espera, 1)} min, tres veces la meta, y el ${pc(D("S0_3_filas").p_espera_10, 0)} de los usuarios espera más de 10 minutos; el 5 % más desafortunado espera más de ${n(D("S0_3_filas").espera_p95, 0)} minutos. La causa es la alta ocupación (ρ ≈ ${n(rho, 2)}) combinada con la variabilidad de los tiempos de uso, que es mayor que la de una exponencial simple porque mezcla tipos muy distintos.`),
  P("Se probaron dos palancas de mejora y los resultados son claros:"),
  ...BUL([
    `**Agregar cajeros con filas independientes.** Un 4.º cajero baja la espera a ${n(D("S1_4_filas").espera, 1)} min (diferencia de ${n(CMP("S0_3_filas", "S1_4_filas").dif, 1)} min, p ${pv(CMP("S0_3_filas", "S1_4_filas").p)}) y un 5.º a ${n(D("S2_5_filas").espera, 1)} min, pero ni siquiera con 5 se cumple la segunda condición (${pc(D("S2_5_filas").p_espera_10)} de usuarios esperando más de 10 min).`,
    `**Organizar una fila única.** Con los mismos 3 cajeros, una fila única baja la espera de ${n(D("S0_3_filas").espera, 1)} a ${n(D("S3_3_fila_unica").espera, 1)} min (diferencia de ${n(CMP("S0_3_filas", "S3_3_fila_unica").dif, 1)} min, p ${pv(CMP("S0_3_filas", "S3_3_fila_unica").p)}), y rinde igual que tener 5 cajeros con filas separadas (diferencia de ${n(Math.abs(CMP("S3_3_fila_unica", "S2_5_filas").dif))} min, p ${pv(CMP("S3_3_fila_unica", "S2_5_filas").p)}). Con filas separadas puede haber un cajero libre mientras otra fila tiene gente; con fila única eso no pasa. Es el efecto de agrupamiento (*pooling*) de la teoría de colas [4].`,
    `**Combinar ambas.** Con 4 cajeros y fila única la espera cae a ${n(D("S4_4_fila_unica").espera, 1)} min y solo el ${pc(D("S4_4_fila_unica").p_espera_10)} de los usuarios espera más de 10 min. Es la **única configuración que cumple el criterio completo**.`,
  ]),
  P("**Estrategia recomendada, aplicada en dos etapas:**"),
  ...BUL([
    `**Etapa 1 (inmediata, sin inversión):** reorganizar cada punto de salida con una sola fila y señalización del tipo "siguiente cajero disponible". La espera promedio pasa de ${n(D("S0_3_filas").espera, 1)} a ${n(D("S3_3_fila_unica").espera, 1)} min y ya cumple la primera condición del criterio, aunque el ${pc(D("S3_3_fila_unica").p_espera_10, 0)} de los usuarios todavía espera más de 10 min.`,
    `**Etapa 2:** instalar **un 4.º cajero** en cada punto, manteniendo la fila única (S4). Con eso se cumplen las dos condiciones y la utilización de los cajeros queda en ${pc(D("S4_4_fila_unica").utilizacion, 0)}, un margen sano para absorber picos de demanda.`,
  ]),
  P(`**Sensibilidad al supuesto del reparto.** Como el enunciado no separa lentos y muy lentos, se repitió el análisis con 15 %/40 % y con 40 %/15 % (Figura 6 y Tabla 8). La conclusión no cambia: con 3 filas independientes la espera nunca baja de ${n(Math.min(...sens.filter((r) => r.escenario === "S0_3_filas").map((r) => r.espera)), 1)} minutos, y la fila única con 3 cajeros siempre queda por debajo de 5 minutos. El escenario más desfavorable (más usuarios muy lentos) es el que más se beneficia de la estrategia.`),
  ...FIG(path.join(FIGS, "fig10_sensibilidad.png"), 6.0, "Figura 6. Sensibilidad de la espera al reparto entre usuarios lentos y muy lentos."),
  CAP_TOP("Tabla 8. Sensibilidad: espera promedio en cola (min) según el reparto lento / muy lento"),
  TABLE(["Reparto", ...escSens.map((e) => CORTO[e])],
    repSens.map((rp) => [rp, ...escSens.map((e) => n(sens.find((r) => r.reparto === rp && r.escenario === e).espera))]),
    [3360, 2000, 2000, 2000]),

  H2("3.4 Punto 4: verificación, calibración y validación"),
  P("La Figura 7 resume el proceso que se siguió. Son tres preguntas distintas que se responden en orden y que pueden obligar a volver atrás [1], [2]:"),
  ...FIG(path.join(FIGS, "fig7_proceso_vv.png"), 6.3, "Figura 7. Proceso de verificación, calibración y validación del modelo."),
  ...BUL([
    "**Verificación: ¿el programa hace lo que dice el modelo conceptual?** Se escribieron 16 pruebas automáticas (test_parqueadero.py) que comprueban que todos los usuarios se atienden exactamente una vez; que ningún cajero atiende a dos personas al mismo tiempo; que la fila es FIFO y nadie se cambia de fila; que en la fila única nadie espera si hay un cajero libre; que el modelo es reproducible con la misma semilla y usa números aleatorios comunes entre escenarios; que más cajeros reducen la espera, y que los algoritmos de transitorio y de réplicas dan el resultado correcto en curvas sintéticas conocidas. También se comprobó la ley de Little.",
    "**Calibración: ¿los datos de entrada que genera el modelo son los de la tabla?** Se generaron 500 jornadas y se compararon las medias y proporciones simuladas con los parámetros (Tabla 9) y los histogramas con la densidad exponencial teórica (Figura 8). Todas las medias quedan a menos del 1 % del valor de la tabla.",
    `**Validación: ¿el modelo representa el sistema real?** Como no hay datos históricos del parqueadero, se validó contra la teoría de colas (Tabla 10 y Figura 9): la utilización simulada (${n(val["Utilización por cajero, simulada"], 2)}) coincide con ρ = ${n(rho, 2)}; la espera simulada (${n(val["Wq simulada, estado estable (min)"], 1)} min) queda entre la fórmula de Pollaczek-Khinchine para M/G/1 (${n(val["Wq fórmula de Pollaczek-Khinchine M/G/1 (min)"], 1)} min) y la aproximación de Kingman para G/G/1 (${n(val["Wq aproximación de Kingman G/G/1 (min)"], 1)} min) [4], y la longitud de la fila es coherente con la ley de Little, Lq = λ·Wq. La validación se completa con el análisis de sensibilidad del supuesto que no da el enunciado (Sección 3.3). Con datos reales de llegadas por hora, el paso siguiente sería comparar contra registros de los cajeros.`,
  ]),
  CAP_TOP("Tabla 9. Calibración de las entradas (500 jornadas simuladas)"),
  TABLE(["Tipo", "Uso medio simulado (min)", "Uso medio de la tabla (min)", "Proporción simulada", "Proporción supuesta"],
    calib.map((r) => [r.tipo, n(r.media_simulada, 3), n(r.media_tabla, 0), pc(r.proporcion_simulada), pc(r.proporcion_supuesta)]),
    [1700, 2000, 2000, 1830, 1830]),
  ...FIG(path.join(FIGS, "fig8_calibracion.png"), 6.4, "Figura 8. Histogramas del tiempo de uso simulado frente a la densidad exponencial con la media de la tabla."),
  CAP_TOP("Tabla 10. Validación contra la teoría de colas (situación actual)"),
  TABLE(["Indicador", "Valor"], Object.entries(val).map(([k, v]) => [k, n(v, v > 50 ? 1 : 3)]), [6900, 2460]),
  ...FIG(path.join(FIGS, "fig9_validacion.png"), 6.0, "Figura 9. Espera y ocupación simuladas frente a los valores teóricos."),
  P("La fórmula de Pollaczek-Khinchine supone llegadas de Poisson, y aquí las llegadas a cada cajero no lo son exactamente (el tiempo entre llegadas depende del tipo), por eso se usa como referencia y no como valor exacto. Que la simulación quede cerca de las dos aproximaciones, y más cerca de la más ajustada, da confianza en el modelo."),

  H2("3.5 Punto 5: eliminación del estado transitorio"),
  P("Con el fin del transitorio identificado en la Sección 2.5, se aplicó el siguiente algoritmo de eliminación, implementado en run_experiments.py:"),
  ...CODE([
    "Entrada: registros de R réplicas piloto (llegada, inicio, fin de cada usuario)",
    "1. Dividir la jornada en intervalos de Δ = 10 min.",
    "2. Para cada intervalo i: Y[i] = espera media de los usuarios que llegaron en i,",
    "   promediada sobre las R réplicas.",
    "3. Suavizar: MM[i] = media de Y[i−w .. i+w] (w = 6; ventana más corta en los extremos).",
    "4. Nivel estable: L = media de MM en la segunda mitad de la jornada.",
    "5. Fin del transitorio: t* = primer i tal que MM[i] >= 0,90 · L.",
    "6. Para cada escenario y réplica: descartar todo usuario con llegada < t*.",
    "7. Calcular todas las estadísticas solo con los usuarios restantes.",
    "8. Número de réplicas: n = máx(n_media_acumulada(±5 %), n_fórmula_IC(±10 %)).",
  ]),
  P(`La Figura 10 compara las medidas seleccionadas antes y después de eliminar el transitorio. A la izquierda, la media acumulada de la espera a lo largo de la jornada: con el transitorio incluido (azul) la curva arranca casi en cero y sube lentamente; nunca alcanza el nivel estable porque arrastra los primeros minutos con filas vacías. Sin el transitorio (verde) la curva arranca ya cerca del nivel estable y se mantiene estable. A la derecha, los promedios de la corrida piloto: con el transitorio, la espera media es de ${n(AD("espera_min").con_transitorio, 1)} min; sin él, ${n(AD("espera_min").sin_transitorio, 1)} min. Incluir el arranque **subestima la espera real en ${pc(subest, 0)}**, lo que podría llevar a la conclusión equivocada de que el sistema funciona mejor de lo que funciona.`),
  ...FIG(path.join(FIGS, "fig3_antes_despues.png"), 6.5, "Figura 10. Espera antes y después de eliminar el transitorio: media acumulada en la jornada (izquierda) y promedios de la corrida piloto (derecha)."),
  CAP_TOP("Tabla 11. Indicadores de la corrida piloto antes y después de eliminar el transitorio"),
  TABLE(["Indicador", "Con transitorio", "Sin transitorio"],
    [["Espera media en cola (min)", "espera_min"], ["Tiempo medio de uso (min)", "uso_min"], ["Tiempo medio en el sistema (min)", "sistema_min"],
     ["Percentil 95 de la espera (min)", "espera_p95_min"], ["Usuarios por réplica", "usuarios_por_replica"]]
      .map(([lab, k]) => [lab, n(AD(k).con_transitorio, 2), n(AD(k).sin_transitorio, 2)]), [4360, 2500, 2500]),
  P("El tiempo de uso del cajero casi no cambia, porque no depende de la congestión; lo que cambia es la espera, que es justamente la variable de decisión. La Figura 2 muestra el mismo efecto sobre las réplicas: la media acumulada con transitorio queda sistemáticamente por debajo de la media sin transitorio."),
);

// 4. Conclusiones
push(
  H1("4. Conclusiones"),
  ...BUL([
    `**Estado estable y corridas.** Con la técnica de la media sobre la variable espera (método de Welch), el transitorio termina a los ${n(TW, 0)} minutos de abrir. La media acumulada se estabiliza con ${EE.n_media_acumulada} réplicas y la fórmula del intervalo de confianza pide ${EE.n_formula_ic}; se usaron ${N} réplicas por escenario.`,
    `**Punto 1.** El cajero ${tmin.k} tiene el menor tiempo promedio de atención (${n(tmin.r.media)} min) y el cajero ${tmax.k} el mayor (${n(tmax.r.media)} min), pero la diferencia no es significativa (p ${pv(anova.p)}): los cajeros son equivalentes.`,
    `**Punto 2.** En el periodo estable se atienden en promedio ${n(TOT.media, 1)} usuarios por réplica entre los tres cajeros: ${n(tend[0].media, 1)} rápidos, ${n(tend[1].media, 1)} normales, ${n(tend[2].media, 1)} lentos y ${n(tend[3].media, 1)} muy lentos, con media y mediana prácticamente iguales.`,
    `**Punto 3.** Los 3 cajeros con filas independientes **no son suficientes**: la espera promedio es de ${n(D("S0_3_filas").espera, 1)} min y casi la mitad de los usuarios espera más de 10. La estrategia recomendada es pasar de inmediato a una fila única (espera de ${n(D("S3_3_fila_unica").espera, 1)} min sin inversión) e instalar un 4.º cajero con fila única, la única configuración que cumple el criterio completo (${n(D("S4_4_fila_unica").espera, 1)} min de espera y ${pc(D("S4_4_fila_unica").p_espera_10)} de usuarios esperando más de 10 min). Agregar cajeros sin cambiar la organización de la fila es la opción menos eficiente.`,
    "**Punto 4.** El modelo se verificó con 16 pruebas automáticas, se calibró contra la tabla de entrada (errores menores al 1 %) y se validó contra la teoría de colas.",
    `**Punto 5.** Eliminar el transitorio es indispensable: sin hacerlo, la espera se subestima en ${pc(subest, 0)}.`,
  ]),
  P("Limitaciones: la demanda es constante durante la jornada (sin horas pico), el reparto entre usuarios lentos y muy lentos es un supuesto, y la validación es teórica porque no hay datos históricos. El modelo queda listo para recalibrarse con registros reales de los cajeros, cambiando solo los parámetros de entrada."),
);

// Referencias y anexo
push(
  H1("Referencias"),
  ...[
    "[1] A. M. Law, *Simulation Modeling and Analysis*, 5th ed. New York, NY, USA: McGraw-Hill Education, 2015.",
    "[2] J. Banks, J. S. Carson, B. L. Nelson y D. M. Nicol, *Discrete-Event System Simulation*, 5th ed. Upper Saddle River, NJ, USA: Pearson, 2010.",
    "[3] P. D. Welch, \"The statistical analysis of simulation results\", en *The Computer Performance Modeling Handbook*, S. S. Lavenberg, Ed. New York, NY, USA: Academic Press, 1983, pp. 268–328.",
    "[4] J. F. Shortle, J. M. Thompson, D. Gross y C. M. Harris, *Fundamentals of Queueing Theory*, 5th ed. Hoboken, NJ, USA: Wiley, 2018.",
    "[5] Team SimPy, \"SimPy: Discrete event simulation for Python\", documentación, versión 4.1. [En línea]. Disponible en: https://simpy.readthedocs.io",
    "[6] C. R. Harris *et al.*, \"Array programming with NumPy\", *Nature*, vol. 585, pp. 357–362, 2020.",
    "[7] P. Virtanen *et al.*, \"SciPy 1.0: Fundamental algorithms for scientific computing in Python\", *Nature Methods*, vol. 17, pp. 261–272, 2020.",
    "[8] J. D. Hunter, \"Matplotlib: A 2D graphics environment\", *Computing in Science & Engineering*, vol. 9, no. 3, pp. 90–95, 2007.",
  ].map((t) => P(t, { noIndent: true })),
  H1("Anexo. Código y reproducibilidad"),
  P("Video de sustentación (Google Drive): " + VIDEO, { noIndent: true }),
  P("Copia del video en GitHub: " + decodeURI(VIDEO_GH), { noIndent: true }),
  P("El código, los datos y las figuras están en el repositorio " + decodeURI(REPO) + ". Las tablas completas (registros de cada usuario en estado estable, resúmenes por cajero, por tipo y por réplica, decisión, comparaciones, sensibilidad, calibración y validación) están en el libro de Excel data/resultados_simulacion_parqueadero.xlsx.", { noIndent: true }),
  ...BUL([
    "parqueadero.py: modelo SimPy (tabla de usuarios, escenarios y lógica de los cajeros).",
    "run_experiments.py: corrida piloto, método de Welch, media acumulada, número de réplicas, eliminación del transitorio y escenarios; escribe los CSV y el Excel en data/.",
    "make_figures.py: genera las figuras con Matplotlib a partir de los CSV.",
    "test_parqueadero.py: pruebas de verificación. demo.py: demostración en consola.",
    "informe/build_informe.js: arma este documento leyendo los mismos CSV.",
  ]),
  P("Código fuente del modelo (parqueadero.py):", { noIndent: true }),
  ...CODE(fs.readFileSync(path.join(ROOT, "parqueadero.py"), "utf8").split(String.fromCharCode(10)).map((l) => l.trimEnd())),
);

Packer.toBuffer(buildDocument(C_)).then((buf) => {
  fs.writeFileSync(path.join(__dirname, SALIDA), buf);
  console.log(SALIDA + " generado");
});
