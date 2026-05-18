// 顶栏：移动端汉堡按钮 + 副标题（仅 sm+ 显示）+ 系统健康灯 + 更新检查 + 紧急停用 + 登出
// iOS PWA：背景色延伸到 safe-area-inset-top（与 black-translucent 状态栏配合），
// 内容区高度仍维持 56px。
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  LogOut,
  Menu,
  Monitor,
  Moon,
  RefreshCw,
  Sun,
  UserCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { logout } from "@/lib/auth";
import { useTheme, type Theme } from "@/lib/theme";
import { HealthDot } from "@/components/HealthDot";
import { KillSwitch } from "./KillSwitch";
import { UpdateDialog } from "./UpdateDialog";

interface TopBarProps {
  username: string;
  onMenuClick: () => void;
}

export function TopBar({ username, onMenuClick }: TopBarProps) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [updateOpen, setUpdateOpen] = useState(false);
  const isStandalone = useStandaloneDisplayMode();
  const mut = useMutation({
    mutationFn: logout,
    onSettled: () => {
      qc.clear();
      nav("/login", { replace: true });
    },
  });

  return (
    <header
      className="
        flex shrink-0 items-center justify-between border-b bg-card
        h-[calc(3.5rem+env(safe-area-inset-top))]
        pt-[env(safe-area-inset-top)]
        pl-[max(1rem,env(safe-area-inset-left))]
        pr-[max(1rem,env(safe-area-inset-right))]
      "
    >
      <div className="flex min-w-0 items-center gap-2">
        {isStandalone ? (
          <div className="md:hidden">
            <div className="text-base font-semibold leading-none">TelePilot</div>
            <div className="mt-0.5 text-[11px] leading-none text-muted-foreground">
              管理控制台
            </div>
          </div>
        ) : (
          /* 移动端汉堡按钮，桌面隐藏；PWA 下由底栏承担导航 */
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={onMenuClick}
            aria-label="打开导航菜单"
          >
            <Menu className="h-5 w-5" />
          </Button>
        )}
        <div className="hidden truncate text-sm text-muted-foreground sm:block">
          TelePilot 管理控制台
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        <HealthDot />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setUpdateOpen(true)}
          aria-label="检查更新"
          title="检查更新"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
        <UpdateDialog open={updateOpen} onOpenChange={setUpdateOpen} />
        <ThemeSwitcher />
        <KillSwitch />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="max-w-[6.75rem] sm:max-w-[8rem]">
              <UserCircle className="mr-1 h-4 w-4 shrink-0" />
              <span className="truncate">{username}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem disabled>已登录账号</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => mut.mutate()}>
              <LogOut className="mr-2 h-4 w-4" /> 退出登录
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

function isStandaloneDisplayMode() {
  if (typeof window === "undefined") {
    return false;
  }
  const navigatorWithStandalone = window.navigator as Navigator & {
    standalone?: boolean;
  };
  return (
    window.matchMedia?.("(display-mode: standalone)").matches === true ||
    navigatorWithStandalone.standalone === true
  );
}

function useStandaloneDisplayMode() {
  const [standalone, setStandalone] = useState(isStandaloneDisplayMode);

  useEffect(() => {
    const media = window.matchMedia?.("(display-mode: standalone)");
    if (!media) {
      return;
    }

    const update = () => setStandalone(isStandaloneDisplayMode());
    update();
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, []);

  return standalone;
}

function ThemeSwitcher() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const Icon = theme === "system" ? Monitor : resolvedTheme === "dark" ? Moon : Sun;

  const options: Array<{ value: Theme; label: string; icon: typeof Sun }> = [
    { value: "light", label: "浅色", icon: Sun },
    { value: "dark", label: "深色", icon: Moon },
    { value: "system", label: "跟随系统", icon: Monitor },
  ];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label="切换主题"
          title="切换主题"
        >
          <Icon className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-36">
        {options.map((item) => (
          <DropdownMenuItem
            key={item.value}
            onSelect={() => setTheme(item.value)}
            className="gap-2"
          >
            <item.icon className="h-4 w-4" />
            <span className="flex-1">{item.label}</span>
            <Check
              className={theme === item.value ? "h-4 w-4" : "h-4 w-4 opacity-0"}
            />
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
