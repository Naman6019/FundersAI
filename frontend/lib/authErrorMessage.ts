type ErrorLike = {
  message?: unknown;
  code?: unknown;
};

export function getAuthErrorMessage(error: unknown): string {
  const errorLike = error && typeof error === 'object' ? (error as ErrorLike) : {};
  const message = typeof errorLike.message === 'string' ? errorLike.message.toLowerCase() : '';
  const code = typeof errorLike.code === 'string' ? errorLike.code.toLowerCase() : '';
  const value = `${code} ${message}`;

  if (value.includes('invalid login credentials')) {
    return 'The email or password is incorrect.';
  }
  if (value.includes('email not confirmed')) {
    return 'Confirm your email before signing in.';
  }
  if (value.includes('user already registered') || value.includes('already been registered')) {
    return 'An account already exists for this email. Try signing in instead.';
  }
  if (value.includes('password') && (value.includes('short') || value.includes('characters'))) {
    return 'Use a stronger password with at least 8 characters.';
  }
  if (value.includes('rate limit') || value.includes('too many requests')) {
    return 'Too many attempts. Wait a moment and try again.';
  }
  if (value.includes('expired') || value.includes('invalid') && value.includes('token')) {
    return 'This link is invalid or has expired. Request a new one.';
  }

  return 'We could not complete that request. Please try again.';
}
