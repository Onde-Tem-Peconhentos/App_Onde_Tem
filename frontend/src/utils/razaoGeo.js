// src/utils/razaoGeo.js
//
// Combina os GeoJSONs de observado/predito num único FeatureCollection com a
// razão predito/observado por município, já com uma cor divergente
// (azul = subestimou, branco = acertou, vermelho = superestimou) calculada
// no cliente — os GeoJSONs de observado/predito, individualmente, já vêm
// com fill_color pronto do backend, mas essa combinação é só feita aqui.

const CLAMP = 3; // acima de 3x (ou abaixo de 1/3) a cor satura — evita que
                   // um único outlier (ex.: 1 caso observado vs. 4 preditos)
                   // domine toda a escala.

function lerp(a, b, t) {
  return Math.round(a + (b - a) * t);
}

/** Cor divergente branco(1)→vermelho (superestimou) / azul(subestimou)→branco(1). */
export function corRazao(razao) {
  if (razao === null || razao === undefined || Number.isNaN(razao)) {
    return [148, 163, 184, 140]; // cinza neutro: razão não calculável
  }

  const r = Math.min(Math.max(razao, 1 / CLAMP), CLAMP);

  if (r >= 1) {
    const t = (r - 1) / (CLAMP - 1);
    return [255, lerp(255, 20, t), lerp(255, 20, t), 190];
  }

  const t = (r - 1 / CLAMP) / (1 - 1 / CLAMP);
  return [lerp(20, 255, t), lerp(90, 255, t), lerp(200, 255, t), 190];
}

/**
 * Calcula a razão predito/observado por município, tratando o caso de
 * observado = 0 (divisão indefinida):
 *   - observado = 0 e predito ≈ 0  → razão = 1 (o modelo acertou "zero casos")
 *   - observado = 0 e predito > 0  → razão = null (não calculável — o modelo
 *     previu casos onde não houve nenhum; sinalizado à parte, nunca como
 *     Infinity)
 *   - observado > 0                → razão = predito / observado, normal
 */
export function calcularRazao(observadoVal, preditoVal) {
  if (observadoVal === null || observadoVal === undefined) return null;
  if (preditoVal === null || preditoVal === undefined) return null;

  if (observadoVal === 0) {
    return Math.abs(preditoVal) < 1e-6 ? 1 : null;
  }

  return preditoVal / observadoVal;
}

/**
 * Junta os FeatureCollections de observado e predito (por `properties.codigo`,
 * o identificador do município presente em ambos) num único FeatureCollection
 * com `observado`, `predito`, `razao` e `fill_color` prontos para o GeoPlot.
 * Retorna null se algum dos dois ainda não estiver disponível.
 */
export function buildRazaoGeoJson(observadoGeo, preditoGeo) {
  if (!observadoGeo?.features || !preditoGeo?.features) return null;

  const preditoPorCodigo = new Map();
  for (const feature of preditoGeo.features) {
    const codigo = feature?.properties?.codigo;
    if (codigo !== undefined && codigo !== null) {
      preditoPorCodigo.set(codigo, feature);
    }
  }

  const features = observadoGeo.features.map((featureObs) => {
    const propsObs = featureObs.properties || {};
    const featurePred = preditoPorCodigo.get(propsObs.codigo);
    const propsPred = featurePred?.properties || {};

    const observado = propsObs.casos_observado ?? null;
    const predito = propsPred.casos_predito ?? null;
    const razao = calcularRazao(observado, predito);

    return {
      ...featureObs,
      properties: {
        ...propsObs,
        municipio: propsObs.municipio ?? propsPred.municipio,
        populacao: propsObs.populacao ?? propsPred.populacao,
        casos_observado: observado,
        casos_predito: predito,
        razao,
        fill_color: corRazao(razao),
      },
    };
  });

  return { type: "FeatureCollection", features };
}
