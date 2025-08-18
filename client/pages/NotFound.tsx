import { useLocation, Link } from "react-router-dom";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AlertTriangle, Home, ArrowLeft } from "lucide-react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname,
    );
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Home
            </Button>
          </Link>
        </div>

        <Card className="border-border/50">
          <CardHeader className="text-center py-12">
            <AlertTriangle className="w-16 h-16 text-accent mx-auto mb-4" />
            <CardTitle className="text-4xl mb-2">404</CardTitle>
            <CardDescription className="text-xl">
              Oops! This page doesn't exist in our trading system.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-12">
            <p className="text-muted-foreground mb-6">
              The page you're looking for might have been moved, deleted, or
              doesn't exist yet.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/">
                <Button className="bg-primary hover:bg-primary/90">
                  <Home className="w-4 h-4 mr-2" />
                  Go Home
                </Button>
              </Link>
              <Link to="/dashboard">
                <Button variant="outline">View Dashboard</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default NotFound;
