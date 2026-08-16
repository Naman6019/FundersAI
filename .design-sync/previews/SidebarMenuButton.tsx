import {
  SidebarProvider,
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuBadge,
  SidebarInset,
  SidebarTrigger,
} from 'marketmind';
import { LayoutDashboard, TrendingUp, PieChart } from 'lucide-react';

const shellStyle: React.CSSProperties = {
  height: 360,
  position: 'relative',
  overflow: 'hidden',
  border: '1px solid #e5e5e5',
};

function Frame({ activeItem }: { activeItem: 'Dashboard' | null }) {
  return (
    <div style={shellStyle}>
      <SidebarProvider>
        <Sidebar>
          <SidebarHeader>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 4px' }}>
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: 6,
                  background: '#1d4ed8',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                FA
              </div>
              <span style={{ fontWeight: 600, fontSize: 13 }}>FundersAI</span>
            </div>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel>Research</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton isActive={activeItem === 'Dashboard'}>
                      <LayoutDashboard />
                      <span>Dashboard</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton>
                      <TrendingUp />
                      <span>Stock Screener</span>
                    </SidebarMenuButton>
                    <SidebarMenuBadge>12</SidebarMenuBadge>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton>
                      <PieChart />
                      <span>Portfolio Overlap</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
        </Sidebar>
        <SidebarInset>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 12 }}>
            <SidebarTrigger />
            <span style={{ fontSize: 13, fontWeight: 600 }}>
              {activeItem ?? 'Overview'}
            </span>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  );
}

export function Default() {
  return <Frame activeItem={null} />;
}

export function Active() {
  return <Frame activeItem="Dashboard" />;
}
