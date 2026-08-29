import { AxiosError, AxiosRequestConfig } from 'axios';
export declare const AXIOS_INSTANCE: import("axios").AxiosInstance;
export declare const customInstance: <T>(config: AxiosRequestConfig, options?: AxiosRequestConfig) => Promise<T>;
export type ErrorType<Error> = AxiosError<Error>;
