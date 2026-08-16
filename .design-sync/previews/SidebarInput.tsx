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
  SidebarInput,
  SidebarInset,
  SidebarTrigger,
} from 'marketmind';
import { LayoutDashboard, TrendingUp } from 'lucide-react';

const shellStyle: React.CSSProperties = {
  height: 320,
  position: 'relative',
  overflow: 'hidden',
  border: '1px solid #e5e5e5',
};

function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div style={shellStyle}>
      <SidebarProvider>
        <Sidebar>
          <SidebarHeader>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 4px 4px' }}>
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
            {children}
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
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
        </Sidebar>
        <SidebarInset>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 12 }}>
            <SidebarTrigger />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Dashboard</span>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  );
}

export function Default() {
  return (
    <Frame>
      <SidebarInput placeholder="Search funds & stocks" />
    </Frame>
  );
}
