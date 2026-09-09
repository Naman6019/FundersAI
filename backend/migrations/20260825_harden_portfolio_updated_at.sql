-- Keep the portfolio timestamp trigger from resolving objects through a mutable
-- session search_path when it runs under a user-facing write.
CREATE OR REPLACE FUNCTION public.handle_portfolio_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;
