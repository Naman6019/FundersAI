import {
  SidebarProvider,
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupAction,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuBadge,
  SidebarMenuAction,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  SidebarInput,
  SidebarSeparator,
  SidebarRail,
  SidebarInset,
  SidebarTrigger,
} from 'marketmind';
import {
  LayoutDashboard,
  TrendingUp,
  PieChart,
  Plus,
  MoreHorizontal,
  Landmark,
  User,
} from 'lucide-react';

const shellStyle: React.CSSProperties = {
  height: 480,
  position: 'relative',
  overflow: 'hidden',
  border: '1px solid #e5e5e5',
};

export function Default() {
  return (
    <div style={shellStyle}>
      <SidebarProvider>
        <Sidebar>
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
              <SidebarGroupAction title="Add watchlist">
                <Plus />
              </SidebarGroupAction>
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
                    <SidebarMenuAction title="More options">
                      <MoreHorizontal />
                    </SidebarMenuAction>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
            <SidebarSeparator />
            <SidebarGroup>
              <SidebarGroupLabel>Mutual Funds</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton>
                      <Landmark />
                      <span>Equity Funds</span>
                    </SidebarMenuButton>
                    <SidebarMenuSub>
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton href="#" isActive>
                          Axis Bluechip Fund
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton href="#">HDFC Flexi Cap</SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton href="#">
                          Parag Parikh Flexi Cap
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    </SidebarMenuSub>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
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
            Main content area rendered inside SidebarInset.
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  );
}
