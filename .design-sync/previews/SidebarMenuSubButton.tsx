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
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  SidebarInset,
  SidebarTrigger,
} from 'marketmind';
import { Landmark } from 'lucide-react';

const shellStyle: React.CSSProperties = {
  height: 360,
  position: 'relative',
  overflow: 'hidden',
  border: '1px solid #e5e5e5',
};

function Frame({ activeFund }: { activeFund: string }) {
  const funds = ['Axis Bluechip Fund', 'HDFC Flexi Cap', 'Parag Parikh Flexi Cap'];
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
              <SidebarGroupLabel>Mutual Funds</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton isActive>
                      <Landmark />
                      <span>Equity Funds</span>
                    </SidebarMenuButton>
                    <SidebarMenuSub>
                      {funds.map((fund) => (
                        <SidebarMenuSubItem key={fund}>
                          <SidebarMenuSubButton href="#" isActive={fund === activeFund}>
                            {fund}
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      ))}
                    </SidebarMenuSub>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
        </Sidebar>
        <SidebarInset>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 12 }}>
            <SidebarTrigger />
            <span style={{ fontSize: 13, fontWeight: 600 }}>{activeFund}</span>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  );
}

export function Default() {
  return <Frame activeFund="" />;
}

export function Active() {
  return <Frame activeFund="Axis Bluechip Fund" />;
}
