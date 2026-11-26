document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".inventory-table thead th[contenteditable='true']").forEach((header) => {
    header.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.isComposing) {
        return;
      }

      event.preventDefault();

      const table = header.closest("table");
      const body = table?.tBodies[0];
      if (!table || !body) {
        return;
      }

      const columnIndex = header.cellIndex;
      const sortType = header.dataset.sortType;
      const direction = header.dataset.sortDirection === "ascending" ? "descending" : "ascending";
      const multiplier = direction === "ascending" ? 1 : -1;
      const rows = Array.from(body.rows).filter((row) => !row.querySelector(".empty-state"));

      const getValue = (row) => {
        const cell = row.cells[columnIndex];
        if (!cell) {
          return "";
        }

        const rawValue = cell.dataset.sortValue || cell.textContent.trim();
        if (sortType === "number") {
          const number = Number(rawValue.replace(/[^0-9.+-]/g, ""));
          return Number.isNaN(number) ? 0 : number;
        }
        if (sortType === "date") {
          const date = Date.parse(rawValue);
          return Number.isNaN(date) ? 0 : date;
        }
        return rawValue.toLocaleLowerCase();
      };

      rows.sort((a, b) => {
        const left = getValue(a);
        const right = getValue(b);
        if (typeof left === "number" && typeof right === "number") {
          return (left - right) * multiplier;
        }
        return left.localeCompare(right, undefined, { numeric: true }) * multiplier;
      });

      rows.forEach((row) => body.appendChild(row));
      header.dataset.sortDirection = direction;
      table.querySelectorAll("thead th[aria-sort]").forEach((sortedHeader) => {
        sortedHeader.removeAttribute("aria-sort");
      });
      header.setAttribute("aria-sort", direction);
    });
  });
});
