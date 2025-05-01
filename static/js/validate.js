document.addEventListener('DOMContentLoaded', () => {
    // For every form on the page
    document.querySelectorAll('form').forEach(form => {
        // Disable native validation UI
        form.setAttribute('novalidate', '');

        const submitBtn = form.querySelector('button[type="submit"]');
        const inputs    = Array.from(form.querySelectorAll('input, textarea'));
        const errors    = {};

        // Prepare an error <div> under each input
        inputs.forEach(input => {
            const err = document.createElement('div');
            err.className = 'form-error';
            // Accessibility: announce errors to screen readers
            err.setAttribute('aria-live', 'polite');
            err.style = 'color:#c00;font-size:0.85rem;margin-top:0.25rem;';
            input.insertAdjacentElement('afterend', err);
            errors[input.name] = err;

            // Validate on each change
            input.addEventListener('input', () => validateField(input, err, form));
        });

        // Prevent submit if invalid
        form.addEventListener('submit', e => {
            let valid = true;
            inputs.forEach(input => {
                if (!validateField(input, errors[input.name], form)) {
                    valid = false;
                }
            });
            if (!valid) e.preventDefault();
        });

        // Enable/disable button as the user types
        form.addEventListener('input', () => {
            submitBtn.disabled = !form.checkValidity();
        });
    });

    function validateField(input, errEl, form) {
        if (input.checkValidity()) {
            // Clear error and accessibility attribute
            errEl.textContent = '';
            input.removeAttribute('aria-invalid');
            return true;
        }
        // Mark invalid for screen readers
        input.setAttribute('aria-invalid', 'true');

        // Required
        if (input.validity.valueMissing) {
            errEl.textContent = 'This field is required.';
        }
        // Email format
        else if (input.validity.typeMismatch && input.type === 'email') {
            errEl.textContent = 'Please enter a valid email address.';
        }
        // Too short
        else if (input.validity.tooShort) {
            errEl.textContent = `Must be at least ${input.minLength} characters.`;
        }
        // Pattern mismatch
        else if (input.validity.patternMismatch) {
            errEl.textContent = 'Invalid format.';
        }
        else {
            errEl.textContent = input.validationMessage;
        }
        return false;
    }
});