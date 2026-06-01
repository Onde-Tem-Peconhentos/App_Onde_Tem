// GeoPlot.jsx

import React, { useMemo } from 'react';
import DeckGL from '@deck.gl/react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { Map } from 'react-map-gl/maplibre';

const INITIAL_VIEW_STATE = {
  latitude: -24.6,
  longitude: -48.25,
  zoom: 5.4,
  pitch: 0,
  bearing: 0
};

const formatBR = (valor) =>
  valor != null
    ? Number(valor).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    : '—';

const GeoPlot = ({ data, target = "map", height = "50vh", title = null }) => {
  // Garante que o GeoJSON é válido
  const isValidData = useMemo(() => {
    if (!data) return false;
    return data.type === "FeatureCollection" && Array.isArray(data.features);
  }, [data]);

  const layers = useMemo(() => {
    if (!isValidData) return [];

    return [
      new GeoJsonLayer({
        id: `geojson-layer-${target}`,
        data,
        pickable: true,
        stroked: true,
        filled: true,
        extruded: false,
        lineWidthMinPixels: 0.5,
        getFillColor: d => d?.properties?.fill_color ?? [200, 200, 200, 150],
        getLineColor: [80, 80, 80, 200],
        updateTriggers: {
          getFillColor: [target, data]
        },
        autoHighlight: true,
        highlightColor: [255, 255, 255, 120],
        fp64: false,
        wrapLongitude: false,
      })
    ];
  }, [data, target, isValidData]);

  const getTooltip = ({ object }) => {
    if (!object || !object.properties) return null;

    const p = object.properties;
    return {
      html: `
        <div style="font-family: sans-serif; font-size: 12px;">
          <strong>${p.municipio || 'Cidade'}</strong><br/>
          POPULAÇÃO: ${formatBR(p.populacao || '—')}<br />
          OBSERVADO: ${formatBR(p.casos_observado)}<br />
          PREDITO: ${formatBR(p.casos_predito)}<br />
          RESÍDUO: ${formatBR(p.casos_residuo)}
        </div>
      `,
      style: {
        backgroundColor: '#000',
        color: '#fff',
        borderRadius: '4px',
        padding: '8px'
      }
    };
  };

  if (!isValidData) {
    return (
      <div style={{
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f8fafc',
        border: '1px dashed #cbd5e1',
        borderRadius: 8,
        fontSize: '0.9rem',
        color: '#64748b'
      }}>
        Mapa indisponível (sem dados válidos)
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height }}>
      {title && (
        <div style={{
          position: 'absolute',
          top: 8,
          left: 8,
          zIndex: 20,
          background: 'rgba(255,255,255,0.9)',
          padding: '6px 10px',
          borderRadius: 6,
          fontWeight: '600',
          boxShadow: '0 1px 4px rgba(0,0,0,0.12)'
        }}>
          {title}
        </div>
      )}

      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
        getTooltip={getTooltip}
        style={{ position: 'absolute', inset: 0 }}
      >
        <Map
          mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
          reuseMaps
        />
      </DeckGL>
    </div>
  );
};

export default React.memo(GeoPlot);