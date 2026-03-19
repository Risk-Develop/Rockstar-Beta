// ==========================
// User Management Script
// ==========================

// DOM Elements
const searchInput = document.getElementById("searchBox");
const tableBody = document.querySelector("table tbody");
const roleModal = document.getElementById('confirmModal');
const yesBtn = document.getElementById('confirmYes');
const noBtn = document.getElementById('confirmNo');

let currentPage = 1;
let currentForm = null;
let originalValue = null;







// ==========================
// Role Dropdown Handlers
// ==========================
function attachRoleDropdownListeners() {
  document.querySelectorAll('.inline-role-form select[name="role"]').forEach(select => {
    select.addEventListener('focus', () => {
      originalValue = select.value;
    });

    select.addEventListener('change', function () {
      currentForm = this.closest('form');
      openRoleModal();
    });
  });
}

function openRoleModal() {
  roleModal.classList.remove('hidden');
  roleModal.classList.add('flex');
}

function closeRoleModal() {
  roleModal.classList.add('hidden');
  roleModal.classList.remove('flex');
  currentForm = null;
  originalValue = null;
}

// ==========================
// Role Modal Actions
// ==========================
yesBtn.addEventListener('click', () => {
  if (currentForm) currentForm.submit();
  closeRoleModal();
});

noBtn.addEventListener('click', () => {
  if (currentForm && originalValue !== null) {
    const select = currentForm.querySelector('select[name="role"]');
    select.value = originalValue;
  }
  closeRoleModal();
});

// ==========================
// Delete Modal Handlers
// ==========================

const deleteModal = document.getElementById("dash-delete-modal");
const modalUsername = document.getElementById("modal-username");
const modalDeleteForm = document.getElementById("modal-delete-form");

// Open delete modal dynamically
function openDeleteModal(username, url) {
  modalUsername.textContent = username;
  modalDeleteForm.action = url;
  deleteModal.classList.remove("hidden");
  deleteModal.classList.add("flex");
}

// Close modal
function closeDeleteModal() {
  deleteModal.classList.add("hidden");
  deleteModal.classList.remove("flex");
  modalUsername.textContent = "";
  modalDeleteForm.action = "";
}

// Event delegation for dynamic buttons
document.addEventListener("click", function (e) {
  if (e.target.classList.contains("delete-btn")) {
    const username = e.target.dataset.username;
    const url = e.target.dataset.url;
    openDeleteModal(username, url);
  }
});

// Optional: close modal when clicking outside the modal content
deleteModal.addEventListener("click", function (e) {
  if (e.target === deleteModal) closeDeleteModal();
});
// ==========================
// Search & Pagination
// ==========================
searchInput.addEventListener("input", function () {
  const query = this.value.trim();
  fetchData(1, query);
});

document.addEventListener("click", function (e) {
  if (e.target.classList.contains("page-btn")) {
    const page = e.target.dataset.page;
    fetchData(page, searchInput.value.trim());
  }
});

// ==========================
// Initial Load
// ==========================
attachRoleDropdownListeners();
attachDeleteButtonListeners();
fetchData(currentPage);
