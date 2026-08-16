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
  SidebarMenuSkeleton,
  SidebarInset,
  SidebarTrigger,
} from 'marketmind';

const shellStyle: React.CSSProperties = {
  height: 360,
  position: 'relative',
  overflow: 'hidden',
  border: '1px solid #e5e5e5',
};

function Frame({ showIcon }: { showIcon: boolean }) {
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
                  {Array.from({ length: 5 }).map((_, i) => (
                    <SidebarMenuItem key={i}>
                      <SidebarMenuSkeleton showIcon={showIcon} />
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
        </Sidebar>
        <SidebarInset>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 12 }}>
            <SidebarTrigger />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Loading funds…</span>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  );
}

export function WithIcon() {
  return <Frame showIcon />;
}

export function TextOnly() {
  return <Frame showIcon={false} />;
}
