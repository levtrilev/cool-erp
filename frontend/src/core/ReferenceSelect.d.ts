interface ReferenceItem {
    id: string;
    name: string;
}
interface ReferenceSelectProps<T extends ReferenceItem> {
    fetchFn: () => Promise<T[]>;
    queryKey: string[];
    value: string | undefined;
    onValueChange: (value: string) => void;
    placeholder?: string;
    disabled?: boolean;
}
/**
 * Универсальный компонент Select для выбора из справочника
 *
 * @example
 * <ReferenceSelect
 *   fetchFn={getTenants}
 *   queryKey={['tenants']}
 *   value={tenantId}
 *   onValueChange={setTenantId}
 *   placeholder="Выберите организацию"
 * />
 */
export declare function ReferenceSelect<T extends ReferenceItem>({ fetchFn, queryKey, value, onValueChange, placeholder, disabled, }: ReferenceSelectProps<T>): import("react").JSX.Element;
export {};
