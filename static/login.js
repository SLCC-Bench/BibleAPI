document.getElementById('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.getElementById('login-submit');
  const error = document.getElementById('login-error');
  button.disabled = true;
  button.textContent = 'Signing in…';
  error.textContent = '';
  try {
    const sessionResponse = await fetch('/auth/session', { cache: 'no-store' });
    if (!sessionResponse.ok) throw new Error('Unable to connect to BibleAPI.');
    const session = await sessionResponse.json();
    const response = await fetch('/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf },
      body: JSON.stringify({
        username: document.getElementById('username').value,
        password: document.getElementById('password').value,
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Unable to sign in.');
    document.getElementById('password').value = '';
    location.replace('/static/admin.html');
  } catch (failure) {
    error.textContent = failure.message || 'Unable to sign in. Please try again.';
  } finally {
    button.disabled = false;
    button.textContent = 'Sign in';
  }
});
