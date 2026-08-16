import {
  SidebarProvider,
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuBadge,
  SidebarInput,
  SidebarSeparator,
  SidebarRail,
  SidebarInset,
  SidebarTrigger,
} from 'marketmind';
import { LayoutDashboard, TrendingUp, PieChart, User } from 'lucide-react';

const shellStyle: React.CSSProperties = {
  height: 480,
  position: 'relative',
  overflow: 'hidden',
  border: '1px solid #e5e5e5',
};

function Nav() {
  return (
    <>
      <SidebarHeader>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 4px' }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: '#1d4ed8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: 12,
              fontWeight: 700,
            }}
          >
            FA
          </div>
          <span style={{ fontWeight: 600, fontSize: 14 }}>FundersAI</span>
        </div>
        <SidebarInput placeholder="Search funds & stocks" />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Research</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton isActive>
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
        <SidebarSeparator />
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton>
              <User />
              <span>Naman Manocha</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </>
  );
}

export function Default() {
  return (
    <div style={shellStyle}>
      <SidebarProvider>
        <Sidebar variant="sidebar" collapsible="offcanvas">
          <Nav />
        </Sidebar>
        <SidebarInset>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: 12,
              borderBottom: '1px solid #e5e5e5',
            }}
          >
            <SidebarTrigger />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Dashboard</span>
          </div>
          <div style={{ padding: 16, fontSize: 13, color: '#6b7280' }}>
            Standard bordered sidebar, docked to the left edge.
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  );
}

export function Floating() {
  return (
    <div style={{ ...shellStyle, background: '#f4f4f5' }}>
      <SidebarProvider>
        <Sidebar variant="floating" collapsible="offcanvas">
          <Nav />
        </Sidebar>
        <SidebarInset>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: 12,
              borderBottom: '1px solid #e5e5e5',
            }}
          >
            <SidebarTrigger />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Dashboard</span>
          </div>
          <div style={{ padding: 16, fontSize: 13, color: '#6b7280' }}>
            Floating variant with rounded corners and a ring, inset from the edge.
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  );
}
