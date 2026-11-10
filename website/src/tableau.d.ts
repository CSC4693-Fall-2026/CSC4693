import type { TableauViz } from '@tableau/embedding-api';

declare global {
  interface HTMLElementTagNameMap {
    'tableau-viz': TableauViz;
  }
}

export {};
