import * as React from "react";
import { FieldPath, FieldValues } from "react-hook-form";
type FormFieldContextValue<TFieldValues extends FieldValues = FieldValues, TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>> = {
    name: TName;
};
export declare const FormFieldContext: React.Context<FormFieldContextValue<FieldValues, string>>;
type FormItemContextValue = {
    id: string;
};
export declare const FormItemContext: React.Context<FormItemContextValue>;
export declare const useFormField: () => {
    invalid: boolean;
    isDirty: boolean;
    isTouched: boolean;
    isValidating: boolean;
    error?: import("react-hook-form").FieldError | undefined;
    id: string;
    name: string;
    formItemId: string;
    formDescriptionId: string;
    formMessageId: string;
};
export {};
