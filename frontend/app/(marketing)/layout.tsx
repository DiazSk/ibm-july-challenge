import { SiteNav, SiteFooter } from "@/components/site-chrome";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteNav />
      {children}
      <SiteFooter />
    </div>
  );
}
