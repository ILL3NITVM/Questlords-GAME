/* Small presentational helpers shared across views. */
export const readout = (label, value, tone = "") =>
  `<div class="readout ${tone}"><span>${label}</span><b>${value}</b></div>`;

export const gauge = (name, val) =>
  `<div class="gauge"><span>${name}</span><div class="bar"><i style="width:${val.toFixed(0)}%"></i></div><b>${val.toFixed(0)}</b></div>`;
