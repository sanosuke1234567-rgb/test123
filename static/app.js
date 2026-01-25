const ingredientsList = document.getElementById('ingredients-list');
const template = document.getElementById('ingredient-template');
const addButton = document.getElementById('add-ingredient');
const previewTotals = {
  carbs: document.getElementById('preview-carbs'),
  protein: document.getElementById('preview-protein'),
  fat: document.getElementById('preview-fat'),
  calories: document.getElementById('preview-calories'),
};

const roundTo = (value) => Math.round(value * 10) / 10;

const updateRow = (row) => {
  const select = row.querySelector('select');
  const weightInput = row.querySelector('input[name="weight_g"]');
  const weight = Number(weightInput.value || 0);
  const option = select.selectedOptions[0];
  const factor = weight / 100;
  const carbs = roundTo(Number(option.dataset.carbs) * factor);
  const protein = roundTo(Number(option.dataset.protein) * factor);
  const fat = roundTo(Number(option.dataset.fat) * factor);
  const calories = roundTo(Number(option.dataset.calories) * factor);

  row.querySelector('[data-field="carbs"]').textContent = carbs;
  row.querySelector('[data-field="protein"]').textContent = protein;
  row.querySelector('[data-field="fat"]').textContent = fat;
  row.querySelector('[data-field="calories"]').textContent = calories;
};

const updateTotals = () => {
  const rows = ingredientsList.querySelectorAll('.ingredient-row');
  const totals = { carbs: 0, protein: 0, fat: 0, calories: 0 };
  rows.forEach((row) => {
    updateRow(row);
    totals.carbs += Number(row.querySelector('[data-field="carbs"]').textContent);
    totals.protein += Number(row.querySelector('[data-field="protein"]').textContent);
    totals.fat += Number(row.querySelector('[data-field="fat"]').textContent);
    totals.calories += Number(row.querySelector('[data-field="calories"]').textContent);
  });

  previewTotals.carbs.textContent = `${roundTo(totals.carbs)} g`;
  previewTotals.protein.textContent = `${roundTo(totals.protein)} g`;
  previewTotals.fat.textContent = `${roundTo(totals.fat)} g`;
  previewTotals.calories.textContent = `${roundTo(totals.calories)} kcal`;
};

const bindRow = (row) => {
  row.querySelector('select').addEventListener('change', updateTotals);
  row.querySelector('input[name="weight_g"]').addEventListener('input', updateTotals);
  row.querySelector('.remove-row').addEventListener('click', () => {
    row.remove();
    updateTotals();
  });
};

const addRow = () => {
  const fragment = template.content.cloneNode(true);
  const row = fragment.querySelector('.ingredient-row');
  ingredientsList.appendChild(fragment);
  bindRow(ingredientsList.lastElementChild);
  updateTotals();
};

addButton.addEventListener('click', addRow);

if (ingredientsList) {
  addRow();
}
