import AdminAccessGate from '@/components/admin/AdminAccessGate';
import AdminLayoutShell from '@/components/admin/AdminLayoutShell';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAccessGate>
      <AdminLayoutShell>{children}</AdminLayoutShell>
    </AdminAccessGate>
  );
}

