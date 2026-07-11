import StudioSidebar from "@/components/layout/StudioSidebar";
import StudioHeader from "@/components/layout/StudioHeader";
import JarvisWidget from "@/components/agent/JarvisWidget";

export default function StudioLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-full" style={{ background: "var(--color-ql-bg)" }}>
      <StudioSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <StudioHeader />
        <main className="flex-1 overflow-y-auto p-6 md:p-10">{children}</main>
      </div>
      <JarvisWidget />
    </div>
  );
}
