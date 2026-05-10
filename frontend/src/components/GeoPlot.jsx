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

const GeoPlot = ({ data, target }) => {
  // 1. Camada Memoizada: Só reconstrói o objeto da camada se o JSON ou o alvo mudarem.
  // Isso evita que o deck.gl recalcule buffers de geometria em cada render do React.
  const layers = useMemo(() => {
    if (!data) return [];

    return [
      new GeoJsonLayer({
        id: 'geojson-layer',
        data,
        pickable: true,
        stroked: true,
        filled: true,
        extruded: false,
        pointType: 'circle',
        lineWidthMinPixels: 0.5,
        
        // Otimização: Acessa a propriedade de cor pré-calculada no seu JSON
        getFillColor: d => d.properties.fill_color || [200, 200, 200, 150],
        getLineColor: [80, 80, 80, 255],
        
        // Performance: Se o JSON mudar, o deck.gl saberá o que atualizar
        updateTriggers: {
          getFillColor: [target]
        },
        
        // Efeito visual de baixo custo via GPU
        autoHighlight: true,
        highlightColor: [255, 255, 255, 100]
      })
    ];
  }, [data, target]);

  // 2. Tooltip Otimizado: Renderizado apenas sob demanda (hover)
  const getTooltip = ({ object }) => {
    if (!object) return null;
    return {
      html: `
        <div style="font-family: sans-serif; font-size: 12px;">
          <strong>${object.properties.municipio || 'Cidade'}</strong><br/>
          POPULAÇÃO: ${object.properties['populacao']}<br />
          ACIDENTES: ${object.properties['observado']}<br />
          PREDITO: ${object.properties['predito']?.toFixed(2)}<br />
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

  return (
    <div style={{ position: 'relative', width: '100%', height: '100vh' }}>
    
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
        getTooltip={getTooltip}
      >
        <Map 
          mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" 
        />
      </DeckGL>
    </div>
  );
};

export default React.memo(GeoPlot); // Evita re-renders se o componente pai mudar