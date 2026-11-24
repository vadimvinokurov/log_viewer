import { levelsShowcase } from "./showcase/levels";
import { filtersShowcase } from "./showcase/filters";
import { emptyShowcase } from "./showcase/empty";
import { menuShowcase } from "./showcase/menu";

/**
 * Dev-only component gallery (rendered for ?show=<name>): the visual harness
 * drives showcase states against this, so components get goldens without
 * being wired into the app shell. Not a user-visible feature (§4 has no
 * showcase UI); reachable only via the URL in headless runs.
 */
const REGISTRY: Record<string, Record<string, React.ReactNode>> = {
  levels: levelsShowcase,
  filters: filtersShowcase,
  empty: emptyShowcase,
  menu: menuShowcase,
};

export default function DevShowcase({ name }: { name: string }) {
  const entries = REGISTRY[name];
  if (!entries) {
    return <p className="empty-state">unknown showcase {JSON.stringify(name)}</p>;
  }
  return (
    <div className="showcase">
      {Object.entries(entries).map(([variant, node]) => (
        <div className="showcase-item" key={variant} data-variant={variant}>
          {node}
        </div>
      ))}
    </div>
  );
}
