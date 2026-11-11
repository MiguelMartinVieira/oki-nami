// Oki-Nami Widget para Scriptable (iOS / iPadOS)
// Copia este código dentro de la aplicación Scriptable en tu iPhone / iPad
// y añade el Widget a tu Pantalla de Inicio.

const DOMAIN = "https://finanzas.tudominio.com"; // <- Reemplaza por tu subdominio real
const API_URL = `${DOMAIN}/app/static/widgets_metrics.json`;

let widget = await createWidget();
if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  widget.presentMedium();
}
Script.complete();

async function createWidget() {
  let w = new ListWidget();
  w.backgroundColor = new Color("#09090B");
  w.setPadding(14, 14, 14, 14);

  let data = null;
  try {
    let req = new Request(API_URL);
    data = await req.loadJSON();
  } catch (e) {
    console.log("Error cargando métricas:", e);
  }

  let m = data && data.metrics ? data.metrics : {
    total_patrimonio_str: "--- €",
    ahorro_ytd_str: "--- €",
    guitar_streak_str: "🔥 - Días"
  };

  // Cabecera
  let header = w.addStack();
  header.layoutHorizontally();
  let title = header.addText("🌊 OKI-NAMI");
  title.font = Font.boldSystemFont(12);
  title.textColor = new Color("#FFFFFF");
  header.addSpacer();
  let streak = header.addText(m.guitar_streak_str);
  streak.font = Font.semiboldSystemFont(11);
  streak.textColor = new Color("#10B981");

  w.addSpacer(8);

  // Tarjeta de Patrimonio
  let pLabel = w.addText("PATRIMONIO TOTAL");
  pLabel.font = Font.mediumSystemFont(9);
  pLabel.textColor = new Color("#A1A1AA");

  let pVal = w.addText(m.total_patrimonio_str);
  pVal.font = Font.boldSystemFont(20);
  pVal.textColor = new Color("#FFFFFF");

  w.addSpacer(6);

  // Fila Ahorro YTD
  let row = w.addStack();
  row.layoutHorizontally();
  
  let yLabel = row.addText("🎯 Ahorro YTD: ");
  yLabel.font = Font.systemFont(11);
  yLabel.textColor = new Color("#A1A1AA");
  
  let yVal = row.addText(m.ahorro_ytd_str);
  yVal.font = Font.boldSystemFont(11);
  yVal.textColor = new Color("#3B82F6");

  return w;
}
