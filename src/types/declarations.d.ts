declare module "lucide-react" {
  import * as React from "react";

  export interface LucideProps extends React.SVGProps<SVGSVGElement> {
    size?: string | number;
    color?: string;
    strokeWidth?: string | number;
    absoluteStrokeWidth?: boolean;
    className?: string;
  }

  export type LucideIcon = React.ForwardRefExoticComponent<
    React.PropsWithoutRef<LucideProps> & React.RefAttributes<SVGSVGElement>
  >;

  export const Play: LucideIcon;
  export const Check: LucideIcon;
  export const X: LucideIcon;
  export const ChevronDown: LucideIcon;
  export const ChevronRight: LucideIcon;
  export const Search: LucideIcon;
  export const AlertCircle: LucideIcon;
  export const Terminal: LucideIcon;
  export const Settings: LucideIcon;
  export const Cpu: LucideIcon;
  export const FileCode: LucideIcon;
  export const Folder: LucideIcon;
  export const RefreshCw: LucideIcon;
  export const Loader2: LucideIcon;
  export const Bug: LucideIcon;
  export const Sparkles: LucideIcon;
  export const ExternalLink: LucideIcon;
  export const Trash2: LucideIcon;
  export const Plus: LucideIcon;
  export const Upload: LucideIcon;
  export const Download: LucideIcon;
  export const Zap: LucideIcon;
  export const Info: LucideIcon;
  export const CheckCircle: LucideIcon;
  export const XCircle: LucideIcon;
  export const Shield: LucideIcon;
  export const Wrench: LucideIcon;
  export const HardDrive: LucideIcon;
  export const Activity: LucideIcon;
  export const BookOpen: LucideIcon;
  export const Copy: LucideIcon;
  export const Database: LucideIcon;
  export const Eye: LucideIcon;
  export const EyeOff: LucideIcon;
  export const HelpCircle: LucideIcon;
  export const Maximize2: LucideIcon;
  export const Minimize2: LucideIcon;
  export const Sliders: LucideIcon;
  export const Sun: LucideIcon;
  export const Moon: LucideIcon;

  // Icons used in layout and pages
  export const Bot: LucideIcon;
  export const FolderKanban: LucideIcon;
  export const Files: LucideIcon;
  export const FlaskConical: LucideIcon;
  export const History: LucideIcon;
  export const LayoutDashboard: LucideIcon;
  export const CircuitBoard: LucideIcon;
  export const Boxes: LucideIcon;
  export const Brain: LucideIcon;
  export const ShieldCheck: LucideIcon;
  export const PanelLeft: LucideIcon;
  export const GitBranch: LucideIcon;
  export const Hammer: LucideIcon;
  export const Square: LucideIcon;
  export const FileText: LucideIcon;
  export const FolderPlus: LucideIcon;
  export const Image: LucideIcon;
  export const Paperclip: LucideIcon;

  const icons: { [key: string]: LucideIcon };
  export default icons;
}
