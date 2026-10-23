import { getTranslator } from "@/lib/i18n/server";

export async function Footer() {
  const { t } = await getTranslator();
  const links = [
    { href: "/problems/", label: t("Problems") },
    { href: "/contests/", label: t("Contests") },
    { href: "/users/", label: t("Ranking") },
    { href: "/blogs/", label: t("Blog") },
  ];
  return (
    <footer className="mt-16 border-t-[3px] border-amber bg-cocoa text-cream">
      <div className="mx-auto flex max-w-[1280px] flex-col gap-6 px-4 py-10 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-heading text-subheading font-extrabold">ThinkAlgo OJ</p>
          <p className="mt-1 text-caption">{t("Practice algorithms every day, fun like a game.")}</p>
        </div>
        <ul className="flex flex-wrap gap-2">
          {links.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="interactive focus-ring inline-flex rounded-full border-2 border-cream px-4 py-1.5 text-caption font-extrabold text-cream hover:bg-amber hover:text-cocoa motion-safe:hover:-translate-y-0.5"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  );
}
