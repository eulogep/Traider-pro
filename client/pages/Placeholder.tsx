import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Construction, ArrowLeft, MessageCircle } from "lucide-react";
import { Link } from "react-router-dom";

interface PlaceholderProps {
  title: string;
  description: string;
  icon?: React.ComponentType<{ className?: string }>;
}

export default function Placeholder({
  title,
  description,
  icon: Icon = Construction,
}: PlaceholderProps) {
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
            <Icon className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
            <CardTitle className="text-2xl mb-2">{title}</CardTitle>
            <CardDescription className="text-lg max-w-2xl mx-auto">
              {description}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center pb-12">
            <p className="text-muted-foreground mb-6">
              This page is under development. Continue prompting to have me
              build out the specific functionality you need.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button className="bg-primary hover:bg-primary/90">
                <MessageCircle className="w-4 h-4 mr-2" />
                Request This Feature
              </Button>
              <Link to="/dashboard">
                <Button variant="outline">Go to Dashboard</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
