"use client";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
} from "@/components/ui/sidebar";
import {
  LayoutDashboard,
  Landmark,
  LineChart,
  Brain,
  ChartSpline,
  Database,
  ShieldCheck,
} from "lucide-react";
import { useChatStore } from "@/store/useChatStore";
import { useEffect } from "react";
import UserProfileDropdown from "@/components/auth/UserProfileDropdown";
import { InfoCard, InfoCardContent, InfoCardDescription, InfoCardTitle, InfoCardMedia } from "@/components/ui/info-card";
import { UserTier } from "@/lib/billing/tiers";
import { DataHealthItem } from "@/components/layout/DashboardLayout";

function statusColorClass(status: string): string {
  const normalized = (status || "").toLowerCase();
  if (["fresh", "synced", "ready", "indexed"].includes(normalized)) return "text-emerald-300";
  if (["lagging", "partial", "processing", "checking"].includes(normalized)) return "text-amber-300";
  if (["stale", "missing", "error"].includes(normalized)) return "text-rose-300";
  return "text-slate-300";
}

export function AppSidebar({
  activeTab,
  setActiveTab,
  dataHealth,
  healthCheckedAt,
  currentTier,
}: {
  activeTab: "overview" | "research";
  setActiveTab: (tab: "overview" | "research") => void;
  dataHealth: DataHealthItem[];
  healthCheckedAt: string | null;
  currentTier: UserTier;
}) {
  const assetType = useChatStore((state) => state.assetType);
  const setAssetType = useChatStore((state) => state.setAssetType);
  const sessions = useChatStore((state) => state.sessions);
  const fetchSessions = useChatStore((state) => state.fetchSessions);
  const loadSessionMessages = useChatStore((state) => state.loadSessionMessages);
  const currentSessionId = useChatStore((state) => state.currentSessionId);
  const resetMessages = useChatStore((state) => state.resetMessages);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const navItems = [
    {
      id: "overview",
      label: "Overview",
      icon: LayoutDashboard,
      isActive: activeTab === "overview",
      onClick: () => setActiveTab("overview"),
    },
    {
      id: "research",
      label: "AI Research",
      icon: Brain,
      isActive: activeTab === "research",
      onClick: () => {
        setActiveTab("research");
        setAssetType("auto");
      },
    },
  ];

  return (
    <Sidebar className="border-r border-white/10 bg-[#0a0a0a]">
      <SidebarHeader className="p-5 border-b border-white/10">
        <div className="flex flex-col gap-1 items-start">
          <img src="/FUNDERSAI-vertical.png" alt="FundersAI Logo" className="h-8 w-auto object-contain origin-left" />
          <p className="text-[11px] uppercase tracking-[0.14em] text-slate-400 pl-1">Research terminal</p>
        </div>
      </SidebarHeader>

      <SidebarContent className="p-2">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.id}>
                  <SidebarMenuButton
                    isActive={item.isActive}
                    onClick={item.onClick}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all ${
                      item.isActive
                        ? "text-white font-bold bg-[#00FF9D]/10 text-[#00FF9D] hover:bg-[#00FF9D]/20 hover:text-[#00FF9D]"
                        : "text-slate-400 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <item.icon className="h-[18px] w-[18px] shrink-0" />
                    <span>{item.label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-4">
          <SidebarGroupLabel className="text-[11px] uppercase tracking-[0.16em] text-slate-400 font-semibold px-3">
            Pipelines
          </SidebarGroupLabel>
          <SidebarGroupContent className="px-3 py-2 space-y-2">
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <ChartSpline className="h-3.5 w-3.5 text-[#00FF9D] shrink-0" />
              <span>Quant + comparison</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <Database className="h-3.5 w-3.5 text-[#00cc7d] shrink-0" />
              <span>Normalized stored data</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <ShieldCheck className="h-3.5 w-3.5 text-slate-400 shrink-0" />
              <span>Research guardrails</span>
            </div>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-4">
          <SidebarGroupLabel className="text-[11px] uppercase tracking-[0.16em] text-slate-400 font-semibold px-3">
            Data health
          </SidebarGroupLabel>
          <SidebarGroupContent className="px-3 py-2 space-y-2">
            {dataHealth.slice(0, 3).map(({ label, status, note }) => (
              <div key={label} className="rounded-lg border border-white/5 bg-white/[0.045] backdrop-blur-md px-2.5 py-1.5 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400" title={note || ""}>{label}</span>
                  <span className={`font-semibold ${statusColorClass(status)}`} title={note || ""}>{status}</span>
                </div>
              </div>
            ))}
            {healthCheckedAt && (
              <p className="mt-2 text-[9px] text-slate-500">
                Checked {new Date(healthCheckedAt).toLocaleString("en-IN", { hour12: false })}
              </p>
            )}
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="mt-4">
          <div className="flex items-center justify-between px-3">
            <SidebarGroupLabel className="text-[11px] uppercase tracking-[0.16em] text-slate-400 font-semibold px-0">
              Recent Chats
            </SidebarGroupLabel>
            <button
              onClick={() => { setActiveTab('overview'); resetMessages(); }}
              className="text-[10px] text-slate-400 hover:text-[#00FF9D] flex items-center gap-1 transition-colors"
            >
              <Brain className="h-3 w-3" />
              New
            </button>
          </div>
          <SidebarGroupContent className="px-3 py-2 space-y-1">
            {sessions.slice(0, 8).map((session) => (
              <button
                key={session.id}
                onClick={() => {
                  setActiveTab('research'); // Switch to research screen to show chat
                  loadSessionMessages(session.id);
                }}
                className={`w-full text-left truncate rounded-lg px-2.5 py-1.5 text-[12px] transition-all ${
                  currentSessionId === session.id
                    ? "bg-[#00FF9D]/10 text-[#00FF9D] font-medium"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                }`}
              >
                {session.title}
              </button>
            ))}
            {sessions.length === 0 && (
              <p className="text-[11px] text-slate-500 px-2 py-1">No recent chats</p>
            )}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4 border-t border-white/10 space-y-4">
        <InfoCard dismissType="forever" storageKey="beta-notice">
          <InfoCardContent>
            <InfoCardTitle>Welcome to Beta!</InfoCardTitle>
            <InfoCardDescription>FundersAI is currently in Beta. Data may be delayed or incomplete.</InfoCardDescription>
            <InfoCardMedia media={[{ type: 'image', src: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop' }]} />
          </InfoCardContent>
        </InfoCard>
        <UserProfileDropdown currentTier={currentTier} />
      </SidebarFooter>
    </Sidebar>
  );
}
