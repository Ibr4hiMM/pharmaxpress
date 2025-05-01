document.addEventListener('DOMContentLoaded', () => {
    // For every form on the page
    document.querySelectorAll('form').forEach(form => {
        // Disable native validation UI
        form.setAttribute('novalidate', '');

        // Password strength helper
        function scorePassword(pw) {
            let score = 0;
            if (pw.length >= 8) score++;
            if (/[a-z]/.test(pw)) score++;
            if (/[A-Z]/.test(pw)) score++;
            if (/\d/.test(pw)) score++;
            if (/[^A-Za-z0-9]/.test(pw)) score++;
            return score;
        }

        // Only on the signup page password field...
        const pwdInput = document.getElementById('password');
        if (pwdInput) {
            const meter = document.getElementById('pwd-strength-meter');
            const errEl = document.getElementById('password-error');
            const submitBtn = pwdInput.closest('form').querySelector('button[type="submit"]');

            pwdInput.addEventListener('input', () => {
                const val = pwdInput.value;
                const score = scorePassword(val);

                // Update the meter and checklist colors
                meter.value = score;
                document.getElementById('pw-len').style.color     = val.length >= 8           ? 'green' : '';
                document.getElementById('pw-lower').style.color   = /[a-z]/.test(val)         ? 'green' : '';
                document.getElementById('pw-upper').style.color   = /[A-Z]/.test(val)         ? 'green' : '';
                document.getElementById('pw-digit').style.color   = /\d/.test(val)            ? 'green' : '';
                document.getElementById('pw-special').style.color = /[^A-Za-z0-9]/.test(val)  ? 'green' : '';

                // **New:** allow form submit as soon as length >= 8
                if (val.length >= 8) {
                    pwdInput.setCustomValidity('');
                    errEl.textContent = '';
                    submitBtn.disabled = false;
                } else {
                    pwdInput.setCustomValidity('Password must be at least 8 characters.');
                    errEl.textContent = 'Password must be at least 8 characters.';
                    submitBtn.disabled = true;
                }
            });
        }

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