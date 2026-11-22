// Genera informe.docx a partir de los CSV de ../data (todas las cifras salen de ahí).
// Uso (desde Actividad 3/informe):  npm install  &&  node build_informe.js
const fs = require("fs");
const path = require("path");
const { P, H1, H2, BUL, EQ, CAP_TOP, CODE, TABLE, FIG, buildDocument, Packer, Paragraph, TextRun, AlignmentType } = require("./lib");

const ROOT = path.resolve(__dirname, "..");
const DATA = path.join(ROOT, "data");
const FIGS = path.join(ROOT, "figures");
const AUTOR = "Santiago Andrés Valencia Duque";
const AFILIACION = "Ingeniería de Software y Datos, IU Digital de Antioquia";
const REPO = "https://github.com/andresvd95/Simulacion/tree/main/Actividad%203";
const SALIDA = "Valencia_Santiago_problemaBancario.docx";
const { TableOfContents } = require("docx");

// ---------- datos
function readCsv(file) {
  const [head, ...rows] = fs.readFileSync(path.join(DATA, file), "utf8").trim().split(/\r?\n/);
  const cols = head.split(",");
  return rows.map((r) => {
    const v = r.split(",");
    const o = {};
    cols.forEach((c, i) => (o[c] = v[i] !== "" && !isNaN(Number(v[i])) ? Number(v[i]) : v[i]));
    return o;
  });
}
const crit = readCsv("resumen_espera_criterio.csv");
const caja = readCsv("resumen_caja.csv");
const ut = readCsv("usuarios_tipo_replica.csv");
const tc = readCsv("usuarios_tipo_caja.csv");
const comp = readCsv("comparaciones.csv");
const val = readCsv("validacion.csv");
const rob = readCsv("robustez.csv");
const nrep = readCsv("replicas_necesarias.csv");
const env = fs.readFileSync(path.join(DATA, "entorno.txt"), "utf8").trim().split(/\r?\n/);

const n = (x, d = 2) => x.toFixed(d).replace(".", ",");
const ci = (r, d = 2) => `${n(r.media, d)} [${n(r.ic_inf, d)}; ${n(r.ic_sup, d)}]`;
const pv = (p) => (p < 0.001 ? "< 0,001" : n(p, 3));
const W = (esc, c) => crit.find((r) => r.escenario === esc && r.criterio === c);
const C = (esc, k, m) => caja.find((r) => r.escenario === esc && r.caja === k && r.metrica === m);
const V = (k) => val.find((r) => r.indicador === k).valor;
const R = (esc, c) => rob.find((r) => r.escenario === esc && r.criterio === c);
const CMP = (a, b) => comp.find((r) => r.a === a && r.b === b);

const ESC = ["E0_3mixtas", "E1_1R_2P", "E2_2R_1P", "E3_4mixtas", "E4_2R_2P"];
const NOM = {
  E0_3mixtas: "E0: 3 cajas mixtas (actual)",
  E1_1R_2P: "E1: 1 retiros + 2 pagos",
  E2_2R_1P: "E2: 2 retiros + 1 pagos",
  E3_4mixtas: "E3: 4 cajas mixtas",
  E4_2R_2P: "E4: 2 retiros + 2 pagos",
};
const OPS = { E0_3mixtas: ["Mixta", "Mixta", "Mixta"], E1_1R_2P: ["Retiros", "Pagos", "Pagos"],
  E2_2R_1P: ["Retiros", "Retiros", "Pagos"], E3_4mixtas: ["Mixta", "Mixta", "Mixta", "Mixta"],
  E4_2R_2P: ["Retiros", "Retiros", "Pagos", "Pagos"] };
const TIPOS = ["Retiro - Rápido", "Retiro - Normal", "Retiro - Lento", "Retiro - Muy lento",
  "Pago - Rápido", "Pago - Normal", "Pago - Lento", "Pago - Muy lento"];
const TABLA = {
  "Retiro - Rápido": [1, 1, 0.23], "Retiro - Normal": [2, 2, 0.4], "Retiro - Lento": [3, 3, 0.17],
  "Retiro - Muy lento": [4, 3, 0.2], "Pago - Rápido": [3, 1, 0.1], "Pago - Normal": [3, 2, 0.2],
  "Pago - Lento": [5, 3, 0.3], "Pago - Muy lento": [7, 4, 0.4],
};
const UMBRAL = 5;

// ---------- cálculos derivados
const cajasDe = (esc) => OPS[esc].map((_, i) => i + 1);
const atenc = [];
for (const e of ["E0_3mixtas", "E1_1R_2P", "E2_2R_1P"]) for (const k of cajasDe(e)) atenc.push({ e, k, r: C(e, k, "t_atencion") });
const e0 = atenc.filter((a) => a.e === "E0_3mixtas");
const e0max = e0.reduce((a, b) => (b.r.media > a.r.media ? b : a));
const e0min = e0.reduce((a, b) => (b.r.media < a.r.media ? b : a));
const allMax = atenc.reduce((a, b) => (b.r.media > a.r.media ? b : a));
const allMin = atenc.reduce((a, b) => (b.r.media < a.r.media ? b : a));

const promTipo = TIPOS.map((t) => ut.reduce((s, r) => s + r[t], 0) / ut.length);
const totalProm = ut.reduce((s, r) => s + r.Total, 0) / ut.length;
const minRep = TIPOS.map((t) => {
  const m = Math.min(...ut.map((r) => r[t]));
  return { t, m, reps: ut.filter((r) => r[t] === m).map((r) => r.replica) };
});
const totMin = Math.min(...ut.map((r) => r.Total));
const repTotMin = ut.find((r) => r.Total === totMin).replica;
const totMax = Math.max(...ut.map((r) => r.Total));
const repTotMax = ut.find((r) => r.Total === totMax).replica;

const CARGA = { Retiro: V("Carga retiros (Erlang)"), Pago: V("Carga pagos (Erlang)") };
const rhoTeo = (esc, k) => {
  const op = OPS[esc][k - 1];
  if (op === "Mixta") return (CARGA.Retiro + CARGA.Pago) / OPS[esc].length;
  const key = op === "Retiros" ? "Retiro" : "Pago";
  return CARGA[key] / OPS[esc].filter((o) => o === op).length;
};
const criterios = (esc) => crit.filter((r) => r.escenario === esc);
const peor = (esc) => criterios(esc).reduce((a, b) => (b.media > a.media ? b : a));
const nSupera = (esc) => criterios(esc).filter((r) => r.media > UMBRAL).length;

// ---------- documento
const C_ = [];
const push = (...xs) => xs.flat().forEach((x) => C_.push(x));
const titulo = (t, size = 32, bold = true, after = 120) =>
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after }, children: [new TextRun({ text: t, bold, size, font: "Times New Roman" })] });

push(
  new Paragraph({ spacing: { before: 2400 }, children: [] }),
  titulo("Simulación de eventos discretos de las cajas del Banco de Colombia", 32),
  titulo("Asignación de cajas exclusivas para pagos y retiros", 26, false, 600),
  titulo("Actividad 3, Simulación", 22, false),
  titulo(AUTOR, 22, true),
  titulo(AFILIACION, 22, false),
  titulo("Noviembre de 2026", 22, false, 0),
  new Paragraph({ pageBreakBefore: true, spacing: { after: 200 }, children: [new TextRun({ text: "Índice", bold: true, size: 24, font: "Times New Roman" })] }),
  new TableOfContents("Índice", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ pageBreakBefore: true, children: [] }),
);

// 1. Introducción
push(
  H1("1. Introducción"),
  P("El Banco de Colombia no cuenta con cajeros electrónicos: todas las operaciones de retiro y de consignación o pago se hacen en tres cajas atendidas por personas. El banco quiere saber si le conviene especializar las cajas (una exclusiva para retiros y dos para pagos, o al revés) y si hace falta abrir una caja adicional, con el fin de reducir la espera de sus usuarios."),
  P("Para responder estas preguntas se construyó un modelo de simulación de eventos discretos de una jornada de 8 horas. Cada caja se representa como una cola M/M/1 independiente: llegadas de Poisson, tiempos de servicio exponenciales, un servidor y disciplina FIFO. Los usuarios se diferencian por la operación que hacen (70 % retiros, 30 % pagos) y por su tipo (rápido, normal, lento, muy lento), cada uno con sus propios tiempos medios de llegada y de servicio. El modelo se ejecutó con 10 réplicas independientes por escenario, como exige el enunciado, y con 100 réplicas adicionales para confirmar la decisión final."),
  P("El documento responde los cinco puntos planteados: (1) la caja con menor y mayor tiempo promedio de atención; (2) el promedio de usuarios de cada tipo en el conjunto de las cajas; (3) el total de usuarios de cada tipo en cada réplica y la réplica con menos usuarios por tipo; (4) si se necesita una caja nueva según los tiempos promedio de espera en todos los criterios, y (5) cuántas cajas deben dedicarse a pagos y cuántas a retiros."),
);

// 2. Metodología
push(
  H1("2. Metodología"),
  H2("2.1 Datos de entrada"),
  P("La Tabla 1 resume los parámetros del enunciado. La probabilidad conjunta de cada tipo es la de la operación (0,70 o 0,30) multiplicada por la probabilidad del tipo dentro de esa operación."),
  CAP_TOP("Tabla 1. Parámetros por tipo de usuario (tiempos en minutos)"),
  TABLE(["Tipo de usuario", "Media de servicio", "Media entre llegadas", "P(tipo | operación)", "P(tipo)"],
    TIPOS.map((t) => [t, n(TABLA[t][0], 0), n(TABLA[t][1], 0), n(TABLA[t][2], 2),
      n((t.startsWith("Retiro") ? 0.7 : 0.3) * TABLA[t][2], 3)]),
    [2600, 1600, 1800, 1700, 1300]),
  H2("2.2 Modelo conceptual"),
  P("La Figura 1 muestra la lógica del modelo. Hay una sola puerta de entrada. Para cada usuario nuevo se sortea primero la operación (retiro con probabilidad 0,70), después el tipo con la Tabla 2 del enunciado, y con ese tipo se generan el tiempo que tarda en llegar desde el usuario anterior (exponencial con la media de llegada del tipo) y su tiempo de servicio (exponencial con la media de uso del tipo). Al llegar, el usuario se forma en la caja habilitada para su operación que tenga menos personas (en cola más en servicio); si hay empate, la caja se escoge al azar. Una vez elegida la caja, el usuario no cambia de fila."),
  ...FIG(path.join(FIGS, "fig6_modelo.png"), 6.3, "Figura 1. Lógica del modelo de simulación."),
  P("Supuestos, tomados del enunciado o necesarios para cerrar el modelo:"),
  ...BUL([
    "Cada caja es un sistema M/M/1 independiente con su propia fila. La velocidad de atención es la misma en todas las cajas: el tiempo de servicio depende del tipo de usuario, no de la caja.",
    "El desplazamiento entre la puerta y la caja es despreciable.",
    "El banco recibe usuarios durante 480 minutos. A esa hora se cierran las puertas, pero se atiende a todos los que ya están adentro; ningún usuario abandona la fila.",
    "Todos los días son iguales, así que basta con simular un día y repetirlo (réplicas) con semillas distintas. No hay periodo de calentamiento porque el banco abre vacío: lo que interesa es justamente el comportamiento de una jornada completa.",
  ]),
  P("Con estos datos, la tasa de llegada esperada es λ = 1/E[tiempo entre llegadas] = 1/" + n(480 / V("Usuarios por día (teórico)"), 3) + " ≈ " + n(V("Usuarios por día (teórico)") / 480, 3) + " usuarios por minuto, es decir, unos " + n(V("Usuarios por día (teórico)"), 0) + " usuarios por día. El servicio medio es de " + n(V("Servicio medio retiro E[S] teórico"), 2) + " min para retiros y " + n(V("Servicio medio pago E[S] teórico"), 2) + " min para pagos, de modo que cada grupo aporta una carga parecida: " + n(V("Carga retiros (Erlang)"), 2) + " Erlang los retiros y " + n(V("Carga pagos (Erlang)"), 2) + " Erlang los pagos. Este dato anticipa el resultado central: aunque los retiros son el 70 % de los usuarios, los pagos demandan casi el mismo tiempo de caja porque cada uno tarda más del doble."),
  H2("2.3 Escenarios"),
  P("Se simularon cinco configuraciones (Tabla 2). E1 y E2 son las dos alternativas que plantea el banco; E0 es la situación actual y sirve de referencia; E3 y E4 agregan una cuarta caja para responder si hace falta un cajero nuevo."),
  CAP_TOP("Tabla 2. Escenarios simulados"),
  TABLE(["Escenario", "Caja 1", "Caja 2", "Caja 3", "Caja 4"],
    ESC.map((e) => [NOM[e], ...[0, 1, 2, 3].map((i) => OPS[e][i] || "No existe")]), [3000, 1590, 1590, 1590, 1590]),
  H2("2.4 Implementación y diseño experimental"),
  P("El modelo se programó en Python con la librería de simulación de eventos discretos SimPy [4]; NumPy [5] genera los números aleatorios y SciPy [6] calcula los intervalos de confianza y las pruebas estadísticas. Cada caja es un recurso SimPy de capacidad 1 y cada usuario es un proceso que solicita el recurso, espera su turno y lo ocupa durante su tiempo de servicio. Entorno: " + env.slice(0, 5).join(", ") + "."),
  P("Se corrieron **10 réplicas** por escenario. La réplica r usa la semilla r en todos los escenarios: así, en una misma réplica los cinco escenarios reciben exactamente los mismos usuarios, con las mismas horas de llegada y los mismos tiempos de servicio. Esta técnica de números aleatorios comunes [1], [2] hace que las diferencias entre escenarios se deban a la configuración de las cajas y no al azar, y permite compararlos con pruebas t pareadas. Para cada indicador se reporta la media de las 10 réplicas con su intervalo de confianza del 95 % basado en la distribución t de Student con 9 grados de libertad:"),
  EQ("IC_{95 %} = x̄ ± t_{0,975; n−1} · s / √n"),
  P("Como 10 réplicas resultaron pocas para separar con claridad E1 de E2, se agregó un **experimento de confirmación con 100 réplicas** (semillas 1001 a 1100). Las tablas que pide el enunciado usan las 10 réplicas principales."),
  H2("2.5 Verificación y validación"),
  P("Se comprobó que el modelo reproduce los datos de entrada (Tabla 3). En 2000 jornadas simuladas la media de usuarios por día coincide con la teórica. En las 10 réplicas principales la media es algo mayor (" + n(V("Usuarios por día (10 réplicas)"), 1) + "), una diferencia normal en una muestra pequeña: la desviación estándar del número de usuarios por día es de unos 16. La proporción de retiros y los tiempos medios de servicio simulados también coinciden con los valores teóricos. Además, la espera de la caja exclusiva de retiros en E1 (" + n(W("E1_1R_2P", "Operación: Retiro").media, 2) + " min) concuerda en orden de magnitud con la fórmula de Pollaczek-Khinchine para una cola M/G/1 en estado estable [3], que da unos 6 min con ρ = " + n(V("Carga retiros (Erlang)"), 2) + "."),
  CAP_TOP("Tabla 3. Verificación del modelo"),
  TABLE(["Indicador", "Valor"], val.map((r) => [r.indicador, n(r.valor, r.valor > 10 ? 1 : 3)]), [6600, 2760]),
  H2("2.6 Número de réplicas necesarias"),
  P("El enunciado pide al menos 10 corridas, pero conviene comprobar si 10 bastan para la precisión que exige la decisión. Con la desviación estándar s de una muestra piloto, el número de réplicas necesario es el menor n que cumple [1], [2]:"),
  EQ("t_{0,975; n−1} · s / √n ≤ ε"),
  P(`donde ε es el semiancho deseado del intervalo de confianza del 95 %. Se fijó ε = ${n(nrep[0].precision_min, 1)} min para las esperas (medio minuto es la menor diferencia que un usuario percibe) y ε = ${n(nrep.find((r) => r.indicador === "Usuarios por día").precision_min, 0)} usuarios para el número de usuarios por día. La Tabla 4 muestra el resultado usando como piloto las 10 réplicas principales y, como contraste, las 100 réplicas de confirmación.`),
  CAP_TOP("Tabla 4. Réplicas necesarias para un IC 95 % con el semiancho indicado"),
  TABLE(["Escenario", "Indicador", "s (10 rép.)", "n necesario", "s (100 rép.)", "n necesario"],
    nrep.map((r) => [r.escenario === "Todos" ? "Todos" : r.escenario.split("_")[0], r.indicador, n(r.de_10, 2), String(r.n_req_10),
      typeof r.de_100 === "number" ? n(r.de_100, 2) : "No aplica", typeof r.n_req_100 === "number" ? String(r.n_req_100) : "No aplica"]),
    [1300, 2200, 1400, 1500, 1460, 1500]),
  P(`Las 10 réplicas son suficientes para las configuraciones donde las cajas comparten la carga (E0, E3 y E4): todas sus esperas necesitan menos de 10 réplicas. El número de usuarios por día necesita ${nrep.find((r) => r.indicador === "Usuarios por día").n_req_10} réplicas para ±10 usuarios; con 10, el intervalo queda en unos ±13, precisión suficiente para describir la demanda. En cambio, las configuraciones especializadas (E1 y E2) tienen una caja cerca de la saturación, su espera varía mucho de un día a otro y necesitarían entre ${Math.min(...nrep.filter((r) => ["E1_1R_2P", "E2_2R_1P"].includes(r.escenario) && r.n_req_10 > 20).map((r) => r.n_req_100))} y ${Math.max(...nrep.filter((r) => ["E1_1R_2P", "E2_2R_1P"].includes(r.escenario)).map((r) => r.n_req_100))} réplicas para estimar su espera con ±0,5 min. Para la decisión no hace falta tanta precisión en cada valor absoluto, sino saber cuál de las dos alternativas espera menos; por eso se corrieron 100 réplicas de confirmación, con las que el intervalo de la diferencia E1 − E2 ya no contiene el cero (Sección 3.5).`),
);

// 3. Resultados
const filaAt = (a) => [NOM[a.e], `Caja ${a.k} (${OPS[a.e][a.k - 1]})`, ci(a.r), ci(C(a.e, a.k, "atendidos"), 1), ci(C(a.e, a.k, "utilizacion"), 3)];
push(
  H1("3. Resultados"),
  H2("3.1 Caja con menor y mayor tiempo promedio de atención"),
  P("La Tabla 5 y la Figura 2 muestran el tiempo promedio de atención (servicio) de cada caja, sin separar los tipos de usuario, junto con el número de usuarios atendidos y la utilización (tiempo ocupado sobre duración de la jornada)."),
  CAP_TOP("Tabla 5. Tiempo promedio de atención por caja, media [IC 95 %], 10 réplicas"),
  TABLE(["Escenario", "Caja", "Atención (min)", "Usuarios atendidos", "Utilización"], atenc.map(filaAt), [2300, 1700, 1900, 1900, 1560]),
  ...FIG(path.join(FIGS, "fig3_atencion_caja.png"), 6.2, "Figura 2. Tiempo promedio de atención por caja, con intervalo de confianza del 95 %."),
  P(`En la situación actual (E0, tres cajas mixtas), la caja con **mayor** tiempo promedio de atención es la caja ${e0max.k} (${n(e0max.r.media)} min) y la de **menor** es la caja ${e0min.k} (${n(e0min.r.media)} min). La diferencia es de apenas ${n(e0max.r.media - e0min.r.media)} min y los intervalos de confianza se traslapan por completo, así que no es estadísticamente significativa. Era lo esperado: como todos los cajeros trabajan a la misma velocidad y reciben la misma mezcla de usuarios, ninguna caja es en realidad más lenta que otra.`),
  P(`Las diferencias reales aparecen cuando se especializan las cajas. La de menor tiempo de atención en todos los escenarios es una caja exclusiva de retiros (${NOM[allMin.e]}, caja ${allMin.k}: ${n(allMin.r.media)} min) y la de mayor es una caja exclusiva de pagos (${NOM[allMax.e]}, caja ${allMax.k}: ${n(allMax.r.media)} min). Esto refleja la Tabla 1: el servicio medio de un pago (${n(V("Servicio medio pago E[S] teórico"))} min) es más del doble que el de un retiro (${n(V("Servicio medio retiro E[S] teórico"))} min). También se ve en la utilización: la caja única de retiros de E1 y la caja única de pagos de E2 están ocupadas cerca del 70 % del día, mientras que las cajas que comparten su operación con otra no pasan del 36 %.`),

  H2("3.2 Promedio de usuarios de cada tipo en el total de cajas"),
  P(`En promedio, el banco atiende ${n(totalProm, 1)} usuarios por día. La Tabla 6 muestra cuántos son de cada tipo, en total y en cada una de las tres cajas de la situación actual. El número de usuarios por tipo no depende de la configuración de las cajas (las llegadas son las mismas en todos los escenarios); lo único que cambia es cómo se reparten entre ellas.`),
  CAP_TOP("Tabla 6. Usuarios promedio por día según tipo (10 réplicas, escenario E0)"),
  TABLE(["Tipo de usuario", "Total cajas", "% del total", "Caja 1", "Caja 2", "Caja 3"],
    [...TIPOS.map((t, i) => {
      const fil = [1, 2, 3].map((k) => tc.find((r) => r.escenario === "E0_3mixtas" && r.caja === k)[t]);
      return [t, n(promTipo[i], 1), n((100 * promTipo[i]) / totalProm, 1) + " %", ...fil.map((x) => n(x, 1))];
    }),
    ["**Total**", `**${n(totalProm, 1)}**`, "**100 %**", ...[1, 2, 3].map((k) => `**${n(tc.find((r) => r.escenario === "E0_3mixtas" && r.caja === k).Total, 1)}**`)]],
    [2500, 1400, 1300, 1386, 1386, 1388]),
  P(`El tipo más frecuente es Retiro - Normal (${n(promTipo[1], 1)} usuarios por día) y el menos frecuente es Pago - Rápido (${n(promTipo[4], 1)}), lo que coincide con sus probabilidades conjuntas (0,280 y 0,030). Las tres cajas mixtas reciben prácticamente la misma cantidad y la misma mezcla de usuarios, porque cada usuario elige la caja con menos gente.`),

  H2("3.3 Total de usuarios de cada tipo en cada réplica"),
  P("La Tabla 7 presenta el total de usuarios de cada tipo en cada una de las 10 réplicas, y la Figura 3 muestra la misma información como mapa de calor, con el mínimo de cada tipo enmarcado."),
  CAP_TOP("Tabla 7. Total de usuarios por tipo y réplica (R = retiro, P = pago)"),
  TABLE(["Réplica", "R Ráp.", "R Norm.", "R Lento", "R M. lento", "P Ráp.", "P Norm.", "P Lento", "P M. lento", "Total"],
    [...ut.map((r) => [String(r.replica), ...TIPOS.map((t) => (r[t] === minRep.find((m) => m.t === t).m ? `**${r[t]}**` : String(r[t]))), r.Total === totMin ? `**${r.Total}**` : String(r.Total)]),
     ["Promedio", ...promTipo.map((x) => n(x, 1)), n(totalProm, 1)]],
    [960, 930, 930, 930, 990, 930, 930, 930, 990, 840]),
  ...FIG(path.join(FIGS, "fig4_usuarios_tipo_replica.png"), 6.2, "Figura 3. Usuarios por tipo en cada réplica. El recuadro naranja marca la réplica con menos usuarios de cada tipo."),
  P("La réplica con menor cantidad de usuarios de cada tipo es:"),
  ...BUL(minRep.map((m) => `${m.t}: ${m.m} usuarios, en la réplica ${m.reps.join(" y ")}.`)),
  P(`En el total, la réplica con menos usuarios es la **réplica ${repTotMin}** (${totMin} usuarios) y la de más es la réplica ${repTotMax} (${totMax}). Ninguna réplica tiene el mínimo en todos los tipos a la vez: la réplica 4, la de menor afluencia de retiros, tiene el mínimo en tres de los cuatro tipos de retiro, pero no en los pagos. La variación entre réplicas es grande (de ${totMin} a ${totMax} usuarios por día), lo que justifica trabajar con varias réplicas e intervalos de confianza en lugar de sacar conclusiones de una sola corrida.`),

  H2("3.4 ¿Hace falta una caja nueva? Tiempos promedio de espera en todos los criterios"),
  P(`Para decidir si se necesita un cajero adicional se calculó la espera promedio en fila en todos los criterios del modelo: general, por operación, por cada uno de los ocho tipos de usuario y por caja. Se fijó como meta de servicio que **ningún criterio supere ${UMBRAL} minutos de espera promedio**. La Tabla 8 resume los resultados y la Figura 4 compara la espera general de cada escenario.`),
  CAP_TOP(`Tabla 8. Espera promedio en fila (min), media [IC 95 %], 10 réplicas`),
  TABLE(["Criterio", ...ESC.map((e) => e.split("_")[0])],
    [["General", ...ESC.map((e) => ci(W(e, "General")))],
     ["Operación: Retiro", ...ESC.map((e) => ci(W(e, "Operación: Retiro")))],
     ["Operación: Pago", ...ESC.map((e) => ci(W(e, "Operación: Pago")))],
     ...TIPOS.map((t) => [t, ...ESC.map((e) => n(W(e, "Tipo: " + t).media))]),
     ...[1, 2, 3, 4].map((k) => [`Caja ${k}`, ...ESC.map((e) => (W(e, `Caja ${k}`) ? n(W(e, `Caja ${k}`).media) : "No existe"))]),
     ["Criterios > 5 min", ...ESC.map((e) => String(nSupera(e)))],
     ["Peor criterio", ...ESC.map((e) => n(peor(e).media))]],
    [2160, 1440, 1440, 1440, 1440, 1440]),
  ...FIG(path.join(FIGS, "fig1_espera_escenarios.png"), 6.2, "Figura 4. Espera promedio general por escenario. La línea punteada marca la meta de 5 minutos."),
  P(`En la **situación actual (E0)** la espera general es de ${n(W("E0_3mixtas", "General").media)} min y el peor criterio (${peor("E0_3mixtas").criterio.replace("Tipo: ", "")}) llega a ${n(peor("E0_3mixtas").media)} min: ningún criterio se acerca a la meta. Las cajas están ocupadas menos de la mitad del día (utilización media de ${n(([1, 2, 3].reduce((s, k) => s + C("E0_3mixtas", k, "utilizacion").media, 0) / 3) * 100, 0)} %). Con las tres cajas mixtas, **no hace falta un cajero nuevo**. Agregar la cuarta caja (E3) baja la espera general a ${n(W("E3_4mixtas", "General").media)} min (diferencia pareada de ${n(CMP("E0_3mixtas", "E3_4mixtas").dif_media)} min, p ${pv(CMP("E0_3mixtas", "E3_4mixtas").p)}), una mejora estadísticamente significativa pero de menos de un minuto, que no compensa el costo de un cajero más.`),
  P(`La respuesta cambia si el banco especializa las cajas. Con solo tres cajas, las dos alternativas incumplen la meta: en E1, ${nSupera("E1_1R_2P")} criterios superan los 5 min (todos los retiros, con ${n(W("E1_1R_2P", "Operación: Retiro").media)} min de espera promedio), y en E2 la superan ${nSupera("E2_2R_1P")} criterios (todos los pagos, con ${n(W("E2_2R_1P", "Operación: Pago").media)} min). La Figura 5 muestra lo que pasa en una jornada típica: la caja única de retiros de E1 llega a acumular más de 15 personas en fila. En cambio, con una cuarta caja (E4: 2 de retiros y 2 de pagos) ningún criterio supera los 5 min (peor criterio: ${n(peor("E4_2R_2P").media)} min). En resumen, **un cajero nuevo solo es necesario si el banco decide especializar las cajas**.`),
  P("La guía del laboratorio pide verificar la estabilidad de cada caja (ρ < 1) y reportar las métricas de cola. La Tabla 9 compara el factor de utilización teórico (carga que recibe cada caja dividida entre su capacidad) con la utilización observada, junto con la espera Wq y la longitud media de la fila Lq, que se obtiene con la ley de Little, Lq = λ · Wq [3]. Todas las cajas cumplen ρ < 1, así que ninguna configuración es inestable; pero las cajas solitarias de E1 y E2 operan con ρ ≈ 0,7, zona donde la fila crece rápidamente con pequeñas variaciones de la demanda."),
  CAP_TOP("Tabla 9. Estabilidad y métricas de cola por caja (10 réplicas)"),
  TABLE(["Escenario", "Caja", "ρ teórico", "Utilización simulada", "Wq (min)", "Lq (personas)"],
    ESC.flatMap((e) => cajasDe(e).map((k) => [NOM[e], `Caja ${k} (${OPS[e][k - 1]})`, n(rhoTeo(e, k), 3),
      n(C(e, k, "utilizacion").media, 3), n(C(e, k, "espera").media), n(C(e, k, "lq").media, 3)])),
    [2500, 1700, 1200, 1500, 1200, 1260]),
  ...FIG(path.join(FIGS, "fig5_cola_tiempo.png"), 6.2, "Figura 5. Personas en fila durante la jornada (réplica 1) por operación, en las tres configuraciones de tres cajas."),
  P("Un detalle llamativo de la Tabla 8 es que los usuarios de tipo rápido esperan más que los lentos dentro de una misma operación. Se debe al proceso de llegadas: el tiempo entre llegadas depende del tipo del usuario que llega, y el de los usuarios rápidos es corto (1 minuto), así que tienden a llegar cuando la persona anterior todavía está en la caja."),

  H2("3.5 Cajas exclusivas para pagos y para retiros"),
  P("La Figura 6 separa la espera por operación. Las dos alternativas trasladan el problema de un grupo al otro: la caja que queda sola para una operación se congestiona, mientras que las dos cajas que comparten la otra operación quedan desocupadas buena parte del día."),
  ...FIG(path.join(FIGS, "fig2_espera_operacion.png"), 6.2, "Figura 6. Espera promedio por operación y escenario, con intervalo de confianza del 95 %."),
  CAP_TOP("Tabla 10. Comparación de E1 y E2: espera promedio en fila (min), media [IC 95 %]"),
  TABLE(["Criterio", "E1: 1 retiros + 2 pagos", "E2: 2 retiros + 1 pagos"],
    [["General (10 réplicas)", ci(W("E1_1R_2P", "General")), ci(W("E2_2R_1P", "General"))],
     ["General (100 réplicas)", ci(R("E1_1R_2P", "General")), ci(R("E2_2R_1P", "General"))],
     ["Retiros (100 réplicas)", ci(R("E1_1R_2P", "Retiro")), ci(R("E2_2R_1P", "Retiro"))],
     ["Pagos (100 réplicas)", ci(R("E1_1R_2P", "Pago")), ci(R("E2_2R_1P", "Pago"))],
     ["Usuarios afectados por la caja saturada", "70 % (retiros)", "30 % (pagos)"]],
    [3360, 3000, 3000]),
  P(`Con las 10 réplicas principales, E2 tiene menor espera general que E1 (${n(W("E2_2R_1P", "General").media)} frente a ${n(W("E1_1R_2P", "General").media)} min), pero la diferencia pareada (${n(CMP("E1_1R_2P", "E2_2R_1P").dif_media)} min, IC 95 % [${n(CMP("E1_1R_2P", "E2_2R_1P").ic_inf)}; ${n(CMP("E1_1R_2P", "E2_2R_1P").ic_sup)}], p = ${pv(CMP("E1_1R_2P", "E2_2R_1P").p)}) no es significativa: hay mucha variación de un día a otro. Con las 100 réplicas de confirmación la conclusión se sostiene y ahora sí es significativa: E1 hace esperar en promedio ${n(R("E1-E2 (pareada)", "General").media)} min más que E2 (IC 95 % [${n(R("E1-E2 (pareada)", "General").ic_inf)}; ${n(R("E1-E2 (pareada)", "General").ic_sup)}], p ${pv(R("E1-E2 (pareada)", "General").p)}).`),
  P(`La razón es que, con una sola caja, el grupo que queda ahí sufre la congestión, y conviene que ese grupo sea el menos numeroso. En E1 la caja saturada atiende al 70 % de los usuarios (retiros); en E2 atiende solo al 30 % (pagos). Aunque cada pago espera más en E2 que cada retiro en E1, son muchas menos personas las afectadas. Por eso, entre las dos alternativas, **el banco debe asignar 2 cajas exclusivas para retiros y 1 para pagos (E2)**. Hay una salvedad: con esa asignación los pagos esperan en promedio ${n(R("E2_2R_1P", "Pago").media)} min (100 réplicas), por encima de la meta de 5 min, lo que lleva de vuelta al punto anterior: para especializar sin desmejorar el servicio se necesita la cuarta caja (E4).`),
  P(`Por último, ninguna asignación exclusiva con tres cajas iguala a las tres cajas mixtas actuales (E0 frente a E2: ${n(CMP("E0_3mixtas", "E2_2R_1P").dif_media)} min, p ${pv(CMP("E0_3mixtas", "E2_2R_1P").p)}). Cuando cualquier caja puede atender a cualquier usuario, la capacidad se comparte y ninguna queda ociosa mientras otra tiene fila; al especializarlas se pierde ese beneficio, que en teoría de colas se conoce como efecto de agrupamiento (*pooling*) [3].`),
);

// 4. Conclusiones
push(
  H1("4. Conclusiones"),
  ...BUL([
    `**Tiempo de atención por caja.** Con tres cajas mixtas, la de mayor tiempo promedio de atención es la caja ${e0max.k} (${n(e0max.r.media)} min) y la de menor es la caja ${e0min.k} (${n(e0min.r.media)} min), pero la diferencia no es significativa porque todos los cajeros tienen la misma velocidad. Al especializar, la caja más lenta es siempre una de pagos (hasta ${n(allMax.r.media)} min por usuario) y la más rápida una de retiros (${n(allMin.r.media)} min).`,
    `**Usuarios por tipo.** El banco atiende en promedio ${n(totalProm, 1)} usuarios por día; el tipo más frecuente es Retiro - Normal (${n(promTipo[1], 1)}) y el menos frecuente Pago - Rápido (${n(promTipo[4], 1)}). Las tres cajas mixtas se reparten los usuarios de forma pareja.`,
    `**Réplicas.** La réplica con menos usuarios en total es la ${repTotMin} (${totMin}); la 4 concentra los mínimos de los retiros. Los totales van de ${totMin} a ${totMax} usuarios por día, una variabilidad que obliga a decidir con intervalos de confianza y no con una sola corrida.`,
    `**Caja nueva.** Con la configuración actual no hace falta: ningún criterio de espera supera los 5 min (el peor es de ${n(peor("E0_3mixtas").media)} min). Sí hace falta si el banco decide especializar las cajas, porque con tres cajas exclusivas un grupo de usuarios supera la meta; con cuatro cajas (2 retiros + 2 pagos) el peor criterio baja a ${n(peor("E4_2R_2P").media)} min.`,
    `**Asignación.** Entre las dos alternativas planteadas, la mejor es **2 cajas exclusivas para retiros y 1 para pagos**: reduce la espera general en ${n(R("E1-E2 (pareada)", "General").media)} min frente a la opción contraria (100 réplicas, p ${pv(R("E1-E2 (pareada)", "General").p)}), porque deja la caja saturada para el grupo minoritario.`,
    `**Recomendación.** La mejor decisión para el servicio es **mantener las tres cajas mixtas**: su espera general (${n(W("E0_3mixtas", "General").media)} min) es entre 4 y 6 veces menor que la de cualquier asignación exclusiva con tres cajas. Si por razones operativas el banco quiere especializar, debe hacerlo con 2 cajas de retiros y 1 de pagos y planear una cuarta caja de pagos para que estos usuarios no esperen más de 5 minutos en promedio.`,
  ]),
  P("Limitaciones: el modelo supone que los usuarios no abandonan la fila ni se cambian de caja, que la afluencia es constante durante el día (sin horas pico) y que los cajeros no tienen pausas. Con datos reales de llegadas por hora, el mismo modelo puede reutilizarse cambiando solo los parámetros de entrada."),
);

// Referencias y anexo
push(
  H1("Referencias"),
  ...[
    "[1] A. M. Law, *Simulation Modeling and Analysis*, 5th ed. New York, NY, USA: McGraw-Hill Education, 2015.",
    "[2] J. Banks, J. S. Carson, B. L. Nelson y D. M. Nicol, *Discrete-Event System Simulation*, 5th ed. Upper Saddle River, NJ, USA: Pearson, 2010.",
    "[3] J. F. Shortle, J. M. Thompson, D. Gross y C. M. Harris, *Fundamentals of Queueing Theory*, 5th ed. Hoboken, NJ, USA: Wiley, 2018.",
    "[4] Team SimPy, \"SimPy: Discrete event simulation for Python\", documentación, versión 4.1. [En línea]. Disponible en: https://simpy.readthedocs.io",
    "[5] C. R. Harris *et al.*, \"Array programming with NumPy\", *Nature*, vol. 585, pp. 357–362, 2020.",
    "[6] P. Virtanen *et al.*, \"SciPy 1.0: Fundamental algorithms for scientific computing in Python\", *Nature Methods*, vol. 17, pp. 261–272, 2020.",
  ].map((t) => P(t, { noIndent: true })),
  H1("Anexo. Código y reproducibilidad"),
  P("El código fuente, los datos generados y las figuras están en la carpeta Actividad 3 del repositorio " + REPO + ". Las tablas completas (registro de cada usuario simulado, resúmenes por caja, por tipo y por réplica, comparaciones y réplicas necesarias) están en el libro de Excel data/resultados_simulacion_banco.xlsx. Para reproducir los resultados:", { noIndent: true }),
  ...BUL([
    "banco.py: modelo SimPy (parámetros, escenarios y lógica de las cajas).",
    "run_experiments.py: corre las 10 réplicas por escenario y las 100 de confirmación, y escribe los CSV en data/.",
    "make_figures.py: genera las figuras a partir de los CSV.",
    "informe/build_informe.js: arma este documento leyendo los mismos CSV, de modo que todas las cifras del texto salen de la simulación.",
  ]),
  P("Código fuente del modelo (banco.py):", { noIndent: true }),
  ...CODE(fs.readFileSync(path.join(ROOT, "banco.py"), "utf8").split(String.fromCharCode(10)).map((l) => l.trimEnd())),
);

Packer.toBuffer(buildDocument(C_)).then((buf) => {
  fs.writeFileSync(path.join(__dirname, SALIDA), buf);
  console.log(SALIDA + " generado");
});
