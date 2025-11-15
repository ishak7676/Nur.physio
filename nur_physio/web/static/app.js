function renderInvoiceCanvas() {
  const canvas = document.getElementById("invoice-canvas");
  if (!canvas) {
    return;
  }

  const rawData = canvas.dataset.invoice;
  if (!rawData) {
    return;
  }

  let invoice;
  try {
    invoice = JSON.parse(rawData);
  } catch (error) {
    console.error("Konnte Rechnungsdaten nicht analysieren:", error);
    return;
  }

  const context = canvas.getContext("2d");
  if (!context) {
    return;
  }

  const width = canvas.width;
  const height = canvas.height;

  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, width, height);

  context.textBaseline = "top";
  context.fillStyle = "#1f2937";
  context.font = "700 28px 'Segoe UI', Roboto, sans-serif";
  context.fillText(`Rechnung ${invoice.invoice_number}`, 48, 60);

  context.font = "16px 'Segoe UI', Roboto, sans-serif";
  context.fillText(`Ausgestellt: ${invoice.issue_date}`, 48, 102);
  context.fillText(`Fällig bis: ${invoice.due_date}`, 48, 126);

  const branchY = 180;
  context.font = "700 18px 'Segoe UI', Roboto, sans-serif";
  context.fillText("Filiale", 48, branchY);
  context.font = "16px 'Segoe UI', Roboto, sans-serif";
  context.fillText(invoice.branch.name || "", 48, branchY + 24);
  const branchAddress = [invoice.branch.street, `${invoice.branch.postal_code || ""} ${invoice.branch.city || ""}`]
    .filter(Boolean)
    .join("\n");
  drawMultilineText(context, branchAddress, 48, branchY + 46, 24);

  const customerX = width / 2;
  context.font = "700 18px 'Segoe UI', Roboto, sans-serif";
  context.fillText("Kunde", customerX, branchY);
  context.font = "16px 'Segoe UI', Roboto, sans-serif";
  const customerName = `${invoice.customer.first_name || ""} ${invoice.customer.last_name || ""}`.trim();
  context.fillText(customerName, customerX, branchY + 24);
  const customerAddress = [
    invoice.customer.street,
    `${invoice.customer.postal_code || ""} ${invoice.customer.city || ""}`,
  ]
    .filter(Boolean)
    .join("\n");
  drawMultilineText(context, customerAddress, customerX, branchY + 46, 24);

  const tableTop = branchY + 140;
  const tableLeft = 48;
  const tableRight = width - 48;
  const headers = ["Leistung", "Menge", "Einzelpreis", "Gesamt"];
  const columnFractions = [0.48, 0.18, 0.17, 0.17];
  const columnWidths = columnFractions.map((fraction) => (tableRight - tableLeft) * fraction);
  const columnStarts = columnWidths.reduce(
    (acc, current, index) => {
      if (index === 0) {
        acc.push(tableLeft);
      } else {
        acc.push(acc[index - 1] + columnWidths[index - 1]);
      }
      return acc;
    },
    /** @type {number[]} */ ([])
  );

  context.lineWidth = 2;
  context.strokeStyle = "#d1d5db";

  const headerHeight = 46;
  context.strokeRect(tableLeft, tableTop, tableRight - tableLeft, headerHeight);
  columnStarts.slice(1).forEach((start) => {
    drawColumnDivider(context, start, tableTop, headerHeight);
  });

  context.font = "700 16px 'Segoe UI', Roboto, sans-serif";
  headers.forEach((header, index) => {
    context.fillText(header, columnStarts[index] + 12, tableTop + 28);
  });

  context.font = "16px 'Segoe UI', Roboto, sans-serif";
  let currentY = tableTop + headerHeight;

  invoice.items.forEach((item) => {
    const descriptionLines = getWrappedLines(
      [item.name || "", item.code ? `Code: ${item.code}` : "", item.description || ""].filter(Boolean),
      columnWidths[0] - 24,
      context
    );
    const rowHeight = Math.max(44, descriptionLines.length * 20 + 16);

    context.strokeRect(tableLeft, currentY, tableRight - tableLeft, rowHeight);
    columnStarts.slice(1).forEach((start) => {
      drawColumnDivider(context, start, currentY, rowHeight);
    });

    drawMultilineText(context, descriptionLines, columnStarts[0] + 12, currentY + 24, 20);
    context.fillText(item.quantity || "", columnStarts[1] + 12, currentY + 24);
    context.fillText(item.unit_price ? `${item.unit_price} €` : "", columnStarts[2] + 12, currentY + 24);
    context.fillText(item.line_total ? `${item.line_total} €` : "", columnStarts[3] + 12, currentY + 24);

    currentY += rowHeight;
  });

  const totalY = currentY + 48;
  context.font = "700 18px 'Segoe UI', Roboto, sans-serif";
  context.textAlign = "right";
  context.fillText("Summe", tableRight - 180, totalY);
  context.font = "700 24px 'Segoe UI', Roboto, sans-serif";
  context.fillText(`${invoice.total} €`, tableRight - 48, totalY);
  context.textAlign = "left";

  if (invoice.notes) {
    const notesTop = totalY + 48;
    context.font = "700 18px 'Segoe UI', Roboto, sans-serif";
    context.fillText("Hinweise", tableLeft, notesTop);
    context.font = "16px 'Segoe UI', Roboto, sans-serif";
    drawMultilineText(context, invoice.notes, tableLeft, notesTop + 28, 22, tableRight - tableLeft);
  }

  const downloadButton = document.getElementById("download-invoice-image");
  if (downloadButton) {
    downloadButton.addEventListener("click", () => {
      const link = document.createElement("a");
      link.href = canvas.toDataURL("image/png");
      link.download = `Rechnung_${invoice.invoice_number}.png`;
      link.click();
    });
  }
}

function drawColumnDivider(context, x, top, height) {
  context.beginPath();
  context.moveTo(x, top);
  context.lineTo(x, top + height);
  context.stroke();
}

function drawMultilineText(context, text, x, y, lineHeight, maxWidth) {
  if (!text) {
    return;
  }

  const lines = Array.isArray(text) ? text : String(text).split("\n");
  const effectiveLineHeight = lineHeight || 20;
  let offset = 0;
  lines.forEach((line) => {
    const fragments = maxWidth ? wrapText(line, maxWidth, context) : [line];
    fragments.forEach((fragment) => {
      context.fillText(fragment, x, y + offset);
      offset += effectiveLineHeight;
    });
  });
}

function wrapText(text, maxWidth, context) {
  const words = text.split(" ");
  const lines = [];
  let currentLine = "";

  words.forEach((word) => {
    const testLine = currentLine ? `${currentLine} ${word}` : word;
    const metrics = context.measureText(testLine);
    if (metrics.width > maxWidth && currentLine) {
      lines.push(currentLine);
      currentLine = word;
    } else {
      currentLine = testLine;
    }
  });

  if (currentLine) {
    lines.push(currentLine);
  }

  return lines;
}

function getWrappedLines(lines, maxWidth, context) {
  if (!lines.length) {
    return [];
  }

  return lines.flatMap((line) => wrapText(line, maxWidth, context));
}

document.addEventListener("DOMContentLoaded", renderInvoiceCanvas);
