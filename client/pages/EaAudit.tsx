import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Activity, HardDrive, ShieldAlert, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Callout, OfflineNotice, Page, PageHeader, Section } from "@/components/layout/Page";
import { EaAuditView } from "@/components/ea/EaAuditView";
import { QuantApiError, quantApi } from "@/lib/quantApi";

/**
 * EA audit — behavioural analysis of a MetaTrader 5 Expert Advisor from its exported report file.
 * The Python engine reads the deal list and looks for grid / martingale mechanisms; nothing is stored,
 * no terminal or broker is contacted.
 */
export default function EaAudit() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => quantApi.health(), retry: false });
  const online = health.isSuccess;
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [contract, setContract] = useState("");

  const mt5 = useQuery({ queryKey: ["mt5-local-files"], queryFn: () => quantApi.listMt5Files(), enabled: online });
  const contractValue = () => {
    const size = contract.trim() === "" ? undefined : Number(contract.replace(",", "."));
    if (size !== undefined && !(size > 0)) throw new QuantApiError(400, "Taille de contrat invalide.");
    return size;
  };
  const auditMt5 = useMutation({ mutationFn: (id: string) => quantApi.analyzeMt5File(id, contractValue()) });
  const audit = useMutation({
    mutationFn: () => {
      if (!file) throw new QuantApiError(400, "Choisissez un rapport MT5 (.html) ou une liste d'opérations (.csv).");
      return quantApi.analyzeEaReport(file, file.name, contractValue());
    },
  });

  return (
    <Page wide>
      <PageHeader
        icon={ShieldAlert}
        title="Audit d'EA"
        status="engine"
        description="Analysez le comportement d'un robot MT5 (Expert Advisor) à partir de son rapport : grille, martingale, positions empilées, et mouvement de l'or qui viderait le compte au pire moment."
      />
      <Callout tone="info" title="Pourquoi cette page">
        Un EA de grille ou de martingale peut afficher des mois de petits gains réguliers, puis tout perdre en une seule tendance :
        son historique de gains ne dit rien de ce risque. Le code d'un .ex5 est fermé, mais ses opérations montrent le mécanisme.
        Aucun fichier n'est conservé, aucun terminal ni courtier n'est contacté.
      </Callout>
      {health.isError && <OfflineNotice />}

      {online && (
        <div className="grid items-start gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
          <aside className="space-y-4">
            <Section title="Rapport à analyser" icon={Upload}>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="ea-file">Fichier (.html, .htm, .csv)</Label>
                  <Input id="ea-file" ref={fileRef} type="file" accept=".html,.htm,.csv,.txt" data-testid="ea-file"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="ea-contract">Taille de contrat (optionnel)</Label>
                  <Input id="ea-contract" inputMode="decimal" placeholder="profil enregistré (XAUUSD : 100 oz)" value={contract}
                    onChange={(e) => setContract(e.target.value)} />
                  <p className="text-xs text-muted-foreground">Unités par lot chez votre courtier : à vérifier dans les spécifications du symbole.</p>
                </div>
                <Button className="w-full" onClick={() => { auditMt5.reset(); audit.mutate(); }} disabled={audit.isPending || !file} data-testid="run-ea-audit">
                  {audit.isPending ? <><Activity className="mr-2 h-4 w-4 animate-spin" />Analyse…</> : <><ShieldAlert className="mr-2 h-4 w-4" />Analyser</>}
                </Button>
                {audit.isError && <p className="text-sm text-red-400" role="alert">{(audit.error as Error).message}</p>}
              </div>
            </Section>
            {mt5.data?.available && (
              <Section title="Rapports trouvés dans votre MT5" icon={HardDrive} testId="mt5-local-files"
                description="Lecture seule des dossiers de rapports du terminal installé sur cet ordinateur.">
                {mt5.data.files.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Aucun rapport .html ou .csv trouvé. Enregistrez un rapport du testeur (voir ci-dessous).</p>
                ) : (
                  <ul className="-mx-2 space-y-1">
                    {mt5.data.files.map((f) => (
                      <li key={f.id}>
                        <button type="button" disabled={f.too_large || auditMt5.isPending} data-testid={`mt5-file-${f.id}`}
                          onClick={() => { audit.reset(); auditMt5.mutate(f.id); }}
                          className="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted/60 disabled:opacity-50">
                          <span className="block truncate font-medium">{f.name}</span>
                          <span className="block text-xs text-muted-foreground">
                            {f.folder} · {new Date(f.modified).toLocaleDateString("fr-FR")} · {(f.bytes / 1024).toFixed(0)} Ko
                            {f.too_large && " · trop volumineux"}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {auditMt5.isPending && <p className="mt-2 text-sm text-muted-foreground">Analyse…</p>}
                {auditMt5.isError && <p className="mt-2 text-sm text-red-400" role="alert">{(auditMt5.error as Error).message}</p>}
              </Section>
            )}
            <Section title="Exporter le rapport depuis MT5">
              <ol className="list-decimal space-y-1.5 pl-4 text-sm text-muted-foreground">
                <li>Testeur de stratégie : lancez le test de l'EA sur XAUUSD, modèle « Chaque tick basé sur des ticks réels ».</li>
                <li>Onglet « Backtest » : clic droit → « Rapport » → enregistrez au format HTML.</li>
                <li>Ou, pour un compte démo : onglet « Historique », affichage par transactions, clic droit → « Rapport » → HTML.</li>
                <li>Déposez le fichier ici. Testez plusieurs périodes, dont des périodes de forte tendance.</li>
              </ol>
            </Section>
          </aside>
          <div>
            {(audit.data ?? auditMt5.data) ? (
              <EaAuditView audit={(audit.data ?? auditMt5.data)!} />
            ) : (
              <p className="text-sm text-muted-foreground">Aucun rapport analysé pour l'instant.</p>
            )}
          </div>
        </div>
      )}
    </Page>
  );
}
