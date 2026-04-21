import { WorkbenchShell } from "@/components/workbench-shell";
import { AuthGate } from "@/components/auth-gate";

export default function DashboardLayout({ children }) {
  return (
    <AuthGate>
      <WorkbenchShell>{children}</WorkbenchShell>
    </AuthGate>
  );
}
