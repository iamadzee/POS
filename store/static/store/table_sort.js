document.addEventListener("DOMContentLoaded", function () {
  var headers = document.querySelectorAll(".inventory-table thead th[contenteditable='true']");
  var sortButtons = document.querySelectorAll(".inventory-table thead button[data-sort-cycle]");
  var originalRows = new WeakMap();

  headers.forEach(function (header) {
    header.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" || event.isComposing) {
        return;
      }

      event.preventDefault();

      var table = header.closest("table");
      if (!table) {
        return;
      }

      var body = table.tBodies[0];
      if (!body) {
        return;
      }

      var direction = header.dataset.sortDirection === "ascending" ? "descending" : "ascending";
      header.dataset.sortDirection = direction;
      sortTableByHeader(header, direction);

      var sortedHeaders = table.querySelectorAll("thead th[aria-sort]");
      sortedHeaders.forEach(function (sortedHeader) {
        sortedHeader.removeAttribute("aria-sort");
      });

      header.setAttribute("aria-sort", direction);
    });
  });
  

  sortButtons.forEach(function (button) {
    var header = button.closest("th");
    var table = button.closest("table");
    var body = table && table.tBodies[0];
    if (!header || !body) {
      return;
    }

    originalRows.set(body, Array.from(body.rows));
    button.addEventListener("click", function () {
      var currentDirection = header.dataset.sortDirection;
      var direction = currentDirection === "ascending"
        ? "descending"
        : currentDirection === "descending"
          ? "none"
          : "ascending";

      table.querySelectorAll("thead th[aria-sort]").forEach(function (sortedHeader) {
        sortedHeader.removeAttribute("aria-sort");
      });

      if (direction === "none") {
        originalRows.get(body).forEach(function (row) {
          body.appendChild(row);
        });
        delete header.dataset.sortDirection;
        button.setAttribute("aria-label", "Sort expiry date ascending");
        button.querySelector(".sort-indicator").textContent = "↕";
        return;
      }

      header.dataset.sortDirection = direction;
      sortTableByHeader(header, direction);
      header.setAttribute("aria-sort", direction);
      button.setAttribute(
        "aria-label",
        "Expiry date sorted " + direction + "; click to sort " +
          (direction === "ascending" ? "descending" : "normal")
      );
      button.querySelector(".sort-indicator").textContent = direction === "ascending" ? "↑" : "↓";
    });
  });

  function sortTableByHeader(header, direction) {
    var table = header.closest("table");
    var body = table && table.tBodies[0];
    if (!body) {
      return;
    }

    var column = header.cellIndex;
    var sortType = header.dataset.sortType;
    var rows = Array.from(body.rows).filter(function (row) {
      return !row.querySelector(".empty-state");
    });

    rows.sort(function (row1, row2) {
      var cell1 = row1.cells[column];
      var cell2 = row2.cells[column];
      var value1 = cell1 ? (cell1.dataset.sortValue || cell1.textContent.trim()) : "";
      var value2 = cell2 ? (cell2.dataset.sortValue || cell2.textContent.trim()) : "";

      if (sortType === "number" || sortType === "date") {
        value1 = sortType === "number"
          ? Number(value1.replace(/[^0-9.+-]/g, "")) || 0
          : Date.parse(value1) || 0;
        value2 = sortType === "number"
          ? Number(value2.replace(/[^0-9.+-]/g, "")) || 0
          : Date.parse(value2) || 0;
        return direction === "ascending" ? value1 - value2 : value2 - value1;
      }

      value1 = value1.toLowerCase();
      value2 = value2.toLowerCase();
      return direction === "ascending"
        ? value1.localeCompare(value2, undefined, { numeric: true })
        : value2.localeCompare(value1, undefined, { numeric: true });
    });

    rows.forEach(function (row) {
      body.appendChild(row);
    });
  }
});
