// ui/src/components/icons.tsx
import React from "react";

export const IconTrendline = (
  <svg width="16" height="16" stroke="currentColor" fill="none">
    <line x1="2" y1="14" x2="14" y2="2" strokeWidth="2" />
  </svg>
);

export const IconHorizontal = (
  <svg width="16" height="16" stroke="currentColor" fill="none">
    <line x1="2" y1="8" x2="14" y2="8" strokeWidth="2" />
  </svg>
);

export const IconVertical = (
  <svg width="16" height="16" stroke="currentColor" fill="none">
    <line x1="8" y1="2" x2="8" y2="14" strokeWidth="2" />
  </svg>
);

export const IconFibRetracement = (
  <svg width="16" height="16" stroke="currentColor" fill="none">
    <line x1="2" y1="4" x2="14" y2="4" strokeWidth="2" />
    <line x1="2" y1="8" x2="14" y2="8" strokeWidth="2" />
    <line x1="2" y1="12" x2="14" y2="12" strokeWidth="2" />
  </svg>
);

export const IconFibExtension = (
  <svg width="16" height="16" stroke="currentColor" fill="none">
    <polyline points="2,14 8,8 14,14" strokeWidth="2" />
  </svg>
);

export const IconFibProjection = (
  <svg width="16" height="16" stroke="currentColor" fill="none">
    <polyline points="2,12 8,4 14,12" strokeWidth="2" />
  </svg>
);

export const IconClear = (
  <svg width="16" height="16" stroke="currentColor" fill="none">
    <line x1="4" y1="4" x2="12" y2="12" strokeWidth="2" />
    <line x1="12" y1="4" x2="4" y2="12" strokeWidth="2" />
  </svg>
);
