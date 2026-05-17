// 应用主框架：左侧 Sidebar（桌面）/ MobileSidebar（移动）+ 顶部 TopBar + 内容 outlet
// 高度用 100dvh：iOS Safari 浏览器模式下避免 100vh 把内容塞到地址栏后面；
//                PWA 全屏模式下行为与 100vh 一致。
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { MOBILE_PRIMARY_NAV, MobileSidebar, Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { GlobalAlertBar } from "./GlobalAlertBar";
import { fetchMe } from "@/lib/auth";
import { Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";

export function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  // 主体框架内顺手取一次当前用户用于顶栏展示
  const { data, isLoading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchMe,
  });

  if (isLoading) {
    return (
      <div className="flex h-[100dvh] items-center justify-center">
        <Spinner className="h-6 w-6 text-primary" />
      </div>
    );
  }

  return (
    <div className="flex h-[100dvh] w-full overflow-hidden bg-background">
      <Sidebar />
      <MobileSidebar open={mobileNavOpen} onOpenChange={setMobileNavOpen} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar
          username={data?.username ?? "未知用户"}
          onMenuClick={() => setMobileNavOpen(true)}
        />
        {/* kill switch 开启时显示全局红色横幅；关闭时不渲染 */}
        <GlobalAlertBar />
        <main
          className="
            flex-1 overflow-auto
            p-4 md:p-6
            pb-[calc(5.75rem+env(safe-area-inset-bottom))]
            sm:pb-[max(1rem,env(safe-area-inset-bottom))]
            pl-[max(1rem,env(safe-area-inset-left))]
            pr-[max(1rem,env(safe-area-inset-right))]
            md:pl-6 md:pr-6
          "
        >
          <div key={location.pathname} className="min-h-full animate-page-enter">
            <Outlet />
          </div>
        </main>
        <nav
          className="
            fixed inset-x-0 bottom-0 z-40 sm:hidden
            pb-[max(0.75rem,env(safe-area-inset-bottom))]
            pl-[max(0.75rem,env(safe-area-inset-left))]
            pr-[max(0.75rem,env(safe-area-inset-right))]
          "
        >
          <div className="liquid-glass liquid-bottom-nav mx-auto grid h-16 max-w-md grid-cols-5 gap-1 p-1.5">
            {MOBILE_PRIMARY_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "liquid-nav-item flex min-w-0 flex-col items-center justify-center gap-0.5 rounded-[1.5rem] text-[10px] font-medium text-muted-foreground transition duration-200",
                    "hover:text-accent-foreground",
                    isActive && "liquid-nav-item-active",
                  )
                }
              >
                <item.icon className="h-4 w-4 shrink-0" />
                <span className="max-w-full truncate">{item.label}</span>
              </NavLink>
            ))}
          </div>
        </nav>
      </div>
    </div>
  );
}
