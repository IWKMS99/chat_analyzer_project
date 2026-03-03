import { useI18n } from "../../i18n/useI18n";

export function HeroPanel() {
  const { t } = useI18n();

  return (
    <section className="surface-elevated p-6">
      <h1 className="text-3xl font-heading text-ink md:text-4xl">{t("app.title")}</h1>
      <p className="mt-3 max-w-3xl text-sm text-slate-700 md:text-base">{t("app.subtitle")}</p>
    </section>
  );
}
