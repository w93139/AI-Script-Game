/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 根据剧本背景生成角色和证据的请求模型
 */
export type GenerateScriptContentRequest = {
    script_id: number;
    theme: string;
    background_story: string;
    player_count: number;
    script_type?: (string | null);
};

