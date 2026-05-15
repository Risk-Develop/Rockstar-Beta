# Exit Interview – Compliance Field Requirements Guide

## Overview

The NDA (`nda_signed`) and NCA (`nca_signed`) fields on the Exit Interview form are
**optional** (not required). This guide documents where "required" behaviour is
implemented across every layer so you can toggle the constraint on or off at any
point without hunting through the codebase.

---

## Where Requirements Are Declared

### 1. Model (`models.py`)

```python
# App/human_resource/models.py  –  ExitInterview model (line ~436)

nda_signed = models.BooleanField(
    default=False,
    help_text="Non-Disclosure Agreement signed",
    # Add `blank=False` here to make the field required at the database/form level.
    # Add `null=False` (default) to prevent NULL in the DB.
)
nca_signed = models.BooleanField(
    default=False,
    help_text="Non-Compete Agreement signed",
    # Same: `blank=False` = required at the model level.
)
```

> **Current state:** `blank=True` (default for `BooleanField`) → optional.
> **Make required:** set `blank=False` on both fields, then run a new migration
> with `python manage.py makemigrations human_resource`.

---

### 2. Django Form (`forms.py`)

```python
# App/human_resource/forms.py  –  ExitInterviewForm (line ~222)

'nda_signed': forms.CheckboxInput(
    attrs={'class': '...'}
    # Add required=True to the widget attrs or override the field:
    # nda_signed = forms.BooleanField(required=True, ...)
),
'nca_signed': forms.CheckboxInput(
    attrs={'class': '...'}
    # Same approach for required=True
),
```

> **Current state:** no `required=True` declared → optional.
> **Make required:** add `required=True` to the field declaration in `ExitInterviewForm`
> (or to the widget), then update the template asterisk if desired.

---

### 3. Template Label (visual `*` indicator)

File: `App/human_resource/templates/hr/default/exit_interview/exit_interview_form.html`

```html
<!-- Step 3 – Compliance section (~line 770) -->
<div class="text-sm font-semibold">
  NDA <span class="font-normal text-gray-500">(Non-Disclosure Agreement)</span>
  <!-- Remove the line below to hide the red asterisk -->
  <span class="field-required">*</span>
</div>

<!-- Same for NCA (~line 800) -->
<div class="text-sm font-semibold">
  NCA <span class="font-normal text-gray-500">(Non-Compete Agreement)</span>
  <span class="field-required">*</span>
</div>
```

> **Current state:** `<span class="field-required">*</span>` is present (set below
> to `<!-- ... -->` to toggle it off; it is already removed in the current revision).

---

### 4. Wizard Navigation Validation (JavaScript)

File: `App/human_resource/templates/hr/default/exit_interview/exit_interview_form.html`
Script block, `validateStep()` function (~line 1125).

```javascript
// REMOVE or COMMENT OUT this block to stop blocking navigation on Step 3:
if (step === 3) {
  const nda = form.querySelector('[name="nda_signed"]');
  const nca = form.querySelector('[name="nca_signed"]');
  [nda, nca].forEach(cb => {
    if (cb && !cb.checked) {
      valid = false;
      if (!firstInvalid) firstInvalid = cb;
    }
  });
}
```

> **Current state:** the block is **removed** → the wizard will let users skip Step 3
> without checking either box. To re-enable, paste the block back into `validateStep()`
> just above the `if (!valid && firstInvalid) {` line.

---

## Quick-Reference Toggle Table

| Layer | File | Change to make required | Change to make optional |
|-------|------|------------------------|------------------------|
| Database / Form | `models.py` `ExitInterview` | `blank=False` + `makemigrations` | `blank=True` (default) |
| Form validation | `forms.py` `ExitInterviewForm` | `required=True` on field | remove `required=True` |
| Visual indicator | `exit_interview_form.html` | uncomment `<span class="field-required">*</span>` | leave commented / removed |
| Wizard block | `exit_interview_form.html` JS | uncomment the `step === 3` block | remove / comment out the block |

---

## Migration Checklist (after model change)

```bash
# 1. Edit the model field(s) in models.py
# 2. Generate a new migration
python manage.py makemigrations human_resource

# 3. Apply to the database
python manage.py migrate human_resource

# 4. Restart the Django development/production server
```

---

## Notes

- Making the fields required at the **model level** (`blank=False`) enforces the
  constraint at the Django form and database layer. Template-only or JS-only
  changes are cosmetic / UX-only and can be bypassed by submitting directly via
  `curl` or the Django admin.
- The **wizard JS validation** runs only on "Next" button clicks. It does **not**
  affect normal form POST submission — server-side validation (model/form) is
  always the authoritative gate.
- To enforce the constraint in the **Django admin**, the model-level `blank=False`
  is sufficient; the admin inherits it automatically.
