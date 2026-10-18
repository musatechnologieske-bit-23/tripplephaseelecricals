(() => {
  const customerSelect = document.querySelector("#id_customer");
  const customerData = document.querySelector("#customer-data");
  if (customerSelect && customerData) {
    const customers = JSON.parse(customerData.textContent);
    const clientFields = {
      name: "#id_client_name",
      phone: "#id_client_phone",
      email: "#id_client_email",
      address: "#id_client_address",
      pin: "#id_client_pin",
    };

    customerSelect.addEventListener("change", () => {
      const customer = customers.find((entry) => String(entry.id) === customerSelect.value);
      if (!customer) return;
      Object.entries(clientFields).forEach(([key, selector]) => {
        const field = document.querySelector(selector);
        if (field) field.value = customer[key] || "";
      });
    });
  }

  const table = document.querySelector("#item-table");
  if (!table) return;

  const rows = document.querySelector("#item-rows");
  const totalForms = document.querySelector("#id_items-TOTAL_FORMS");
  const template = document.querySelector("#empty-item-row");
  const vatCheckbox = document.querySelector("#id_apply_vat");
  const vatRate = Number(table.dataset.vatRate || 0);
  const money = (cents) => (cents / 100).toLocaleString("en-KE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  function updateTotals() {
    let subtotalCents = 0;
    rows.querySelectorAll(".item-row").forEach((row) => {
      if (row.hidden || row.querySelector('input[type="checkbox"]').checked) return;
      const quantity = Number(row.querySelector(".quantity-input").value || 0);
      const price = Number(row.querySelector(".price-input").value || 0);
      const lineCents = Math.round(quantity * price * 100);
      row.querySelector(".line-total").textContent = money(lineCents);
      subtotalCents += lineCents;
    });
    const vatCents = vatCheckbox.checked ? Math.round(subtotalCents * vatRate / 100) : 0;
    document.querySelector("#subtotal-preview").textContent = money(subtotalCents);
    document.querySelector("#vat-preview").textContent = money(vatCents);
    document.querySelector("#vat-preview-row").hidden = !vatCheckbox.checked;
    document.querySelector("#total-preview").textContent = money(subtotalCents + vatCents);
  }

  function addItemRow(afterRow = null) {
    const formIndex = Number(totalForms.value);
    const newRow = template.innerHTML.replaceAll("__prefix__", formIndex);
    if (afterRow) {
      afterRow.insertAdjacentHTML("afterend", newRow);
    } else {
      rows.insertAdjacentHTML("beforeend", newRow);
    }
    totalForms.value = formIndex + 1;
    updateTotals();
  }

  rows.addEventListener("input", updateTotals);
  rows.addEventListener("change", (event) => {
    if (event.target.matches('input[type="checkbox"]')) {
      event.target.closest(".item-row").hidden = event.target.checked;
    }
    updateTotals();
  });
  rows.addEventListener("click", (event) => {
    const addButton = event.target.closest(".add-item-row");
    if (addButton) addItemRow(addButton.closest(".item-row"));
  });
  vatCheckbox.addEventListener("change", updateTotals);
  document.querySelector("#add-item").addEventListener("click", () => addItemRow());
  updateTotals();
})();
