import { describe, expect, it } from 'vitest';
import { GisFeatureCollection } from '../../../../core/models/gis.model';
import { boundsOf, metresForZoom, zoomForMetres } from './gis-cesium-map';

const collection = (...geometries: GeoJSON.Geometry[]): GisFeatureCollection => ({
  type: 'FeatureCollection',
  features: geometries.map((geometry) => ({ type: 'Feature', geometry, properties: {} })),
});

describe('GIS map helpers', () => {
  it('finds the bounds across every geometry type', () => {
    const box = boundsOf([
      collection(
        { type: 'Point', coordinates: [79.5, 18] },
        { type: 'MultiPolygon', coordinates: [[[[78, 17], [80, 17], [80, 19], [78, 17]]]] },
        { type: 'GeometryCollection', geometries: [{ type: 'LineString', coordinates: [[77, 16], [79, 18]] }] },
      ),
      undefined,
    ]);
    expect(box).toEqual([77, 16, 80, 19]);
  });

  it('has no bounds without data', () => {
    expect(boundsOf([collection(), undefined])).toBeNull();
  });

  it('converts zoom levels both ways and keeps them whole and in range', () => {
    expect(zoomForMetres(metresForZoom(12))).toBe(12);
    expect(zoomForMetres(1)).toBe(20);
    expect(zoomForMetres(1e12)).toBe(1);
  });
});
