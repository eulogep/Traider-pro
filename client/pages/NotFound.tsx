import { Link, useLocation } from "react-router-dom";
import { Compass, FlaskConical, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Page } from "@/components/layout/Page";

const NotFound = () => {
  const { pathname } = useLocation();
  return (
    <Page className="flex min-h-[70vh] items-center justify-center">
      <div className="max-w-md space-y-4 text-center" data-testid="not-found">
        <Compass className="mx-auto h-12 w-12 text-muted-foreground" />
        <p className="text-5xl font-bold tracking-tight">404</p>
        <h1 className="text-lg font-semibold">Cette page n'existe pas</h1>
        <p className="text-sm text-muted-foreground">
          Aucune page ne correspond à <code className="rounded bg-muted px-1.5 py-0.5">{pathname}</code>.
        </p>
        <div className="flex flex-wrap justify-center gap-3 pt-2">
          <Button asChild>
            <Link to="/"><Home className="mr-2 h-4 w-4" />Accueil</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/backtest"><FlaskConical className="mr-2 h-4 w-4" />Backtests</Link>
          </Button>
        </div>
      </div>
    </Page>
  );
};

export default NotFound;
