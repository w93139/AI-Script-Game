/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { APIResponse_BatchEditResponse_ } from '../models/APIResponse_BatchEditResponse_';
import type { APIResponse_dict_ } from '../models/APIResponse_dict_';
import type { APIResponse_Dict_str__Any__ } from '../models/APIResponse_Dict_str__Any__';
import type { APIResponse_EditResultResponse_ } from '../models/APIResponse_EditResultResponse_';
import type { APIResponse_list_ScriptCharacter__ } from '../models/APIResponse_list_ScriptCharacter__';
import type { APIResponse_ParsedInstructionsResponse_ } from '../models/APIResponse_ParsedInstructionsResponse_';
import type { APIResponse_ScriptCharacter_ } from '../models/APIResponse_ScriptCharacter_';
import type { APIResponse_str_ } from '../models/APIResponse_str_';
import type { BatchEditRequest } from '../models/BatchEditRequest';
import type { Body_upload_file_api_files_upload_post } from '../models/Body_upload_file_api_files_upload_post';
import type { CharacterCreateRequest } from '../models/CharacterCreateRequest';
import type { CharacterPromptRequest } from '../models/CharacterPromptRequest';
import type { CharacterUpdateRequest } from '../models/CharacterUpdateRequest';
import type { CreateFusionSessionRequest } from '../models/CreateFusionSessionRequest';
import type { EvidenceCreateRequest } from '../models/EvidenceCreateRequest';
import type { EvidencePromptRequest } from '../models/EvidencePromptRequest';
import type { EvidenceUpdateRequest } from '../models/EvidenceUpdateRequest';
import type { ExecuteInstructionRequest } from '../models/ExecuteInstructionRequest';
import type { FusionActionRequest } from '../models/FusionActionRequest';
import type { GenerateSuggestionRequest } from '../models/GenerateSuggestionRequest';
import type { LocationPromptRequest } from '../models/LocationPromptRequest';
import type { ParseInstructionRequest } from '../models/ParseInstructionRequest';
import type { PasswordChange } from '../models/PasswordChange';
import type { PhoneLogin } from '../models/PhoneLogin';
import type { RefreshRequest } from '../models/RefreshRequest';
import type { ScriptLocation } from '../models/ScriptLocation';
import type { SelectCharacterRequest } from '../models/SelectCharacterRequest';
import type { SmsCodeRequest } from '../models/SmsCodeRequest';
import type { SmsCodeResponse } from '../models/SmsCodeResponse';
import type { Token } from '../models/Token';
import type { UserBrief } from '../models/UserBrief';
import type { UserLogin } from '../models/UserLogin';
import type { UserRegister } from '../models/UserRegister';
import type { UserResponse } from '../models/UserResponse';
import type { UserUpdate } from '../models/UserUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class Service {
    /**
     * Parse Instruction
     * 解析用户的自然语言指令（经 ScriptEditingAgent 计划模式：只校验不落库）
     * @param requestBody
     * @returns APIResponse_ParsedInstructionsResponse_ Successful Response
     * @throws ApiError
     */
    public static parseInstructionApiScriptEditorParseInstructionPost(
        requestBody: ParseInstructionRequest,
    ): CancelablePromise<APIResponse_ParsedInstructionsResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/script-editor/parse-instruction',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Execute Instruction
     * 执行单个编辑指令
     * @param requestBody
     * @returns APIResponse_EditResultResponse_ Successful Response
     * @throws ApiError
     */
    public static executeInstructionApiScriptEditorExecuteInstructionPost(
        requestBody: ExecuteInstructionRequest,
    ): CancelablePromise<APIResponse_EditResultResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/script-editor/execute-instruction',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Batch Edit
     * 批量执行编辑指令
     * @param requestBody
     * @returns APIResponse_BatchEditResponse_ Successful Response
     * @throws ApiError
     */
    public static batchEditApiScriptEditorBatchEditPost(
        requestBody: BatchEditRequest,
    ): CancelablePromise<APIResponse_BatchEditResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/script-editor/batch-edit',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Generate Suggestion
     * 生成AI编辑建议
     * @param requestBody
     * @returns APIResponse_str_ Successful Response
     * @throws ApiError
     */
    public static generateSuggestionApiScriptEditorGenerateSuggestionPost(
        requestBody: GenerateSuggestionRequest,
    ): CancelablePromise<APIResponse_str_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/script-editor/generate-suggestion',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Editing Context
     * 获取剧本编辑上下文信息
     * @param scriptId
     * @returns APIResponse_Dict_str__Any__ Successful Response
     * @throws ApiError
     */
    public static getEditingContextApiScriptEditorScriptScriptIdEditingContextGet(
        scriptId: number,
    ): CancelablePromise<APIResponse_Dict_str__Any__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/script-editor/script/{script_id}/editing-context',
            path: {
                'script_id': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Validate Script
     * 验证剧本完整性
     * @param scriptId
     * @returns APIResponse_Dict_str__Any__ Successful Response
     * @throws ApiError
     */
    public static validateScriptApiScriptEditorScriptScriptIdValidationGet(
        scriptId: number,
    ): CancelablePromise<APIResponse_Dict_str__Any__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/script-editor/script/{script_id}/validation',
            path: {
                'script_id': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建证据
     * 为指定剧本创建新证据
     * @param scriptId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createEvidenceApiEvidenceScriptIdEvidencePost(
        scriptId: number,
        requestBody: EvidenceCreateRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/evidence/{script_id}/evidence',
            path: {
                'script_id': scriptId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新证据
     * 更新指定证据的信息
     * @param scriptId
     * @param evidenceId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateEvidenceApiEvidenceScriptIdEvidenceEvidenceIdPut(
        scriptId: number,
        evidenceId: number,
        requestBody: EvidenceUpdateRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/evidence/{script_id}/evidence/{evidence_id}',
            path: {
                'script_id': scriptId,
                'evidence_id': evidenceId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除证据
     * 删除指定证据
     * @param scriptId
     * @param evidenceId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteEvidenceApiEvidenceScriptIdEvidenceEvidenceIdDelete(
        scriptId: number,
        evidenceId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/evidence/{script_id}/evidence/{evidence_id}',
            path: {
                'script_id': scriptId,
                'evidence_id': evidenceId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 生成证据图片提示词
     * 使用LLM生成证据图片的提示词
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static generateEvidencePromptApiEvidenceEvidenceGeneratePromptPost(
        requestBody: EvidencePromptRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/evidence/evidence/generate-prompt',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建角色
     * 为指定剧本创建新角色
     * @param scriptId
     * @param requestBody
     * @returns APIResponse_ScriptCharacter_ Successful Response
     * @throws ApiError
     */
    public static createCharacterApiCharactersScriptIdCharactersPost(
        scriptId: number,
        requestBody: CharacterCreateRequest,
    ): CancelablePromise<APIResponse_ScriptCharacter_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/characters/{script_id}/characters',
            path: {
                'script_id': scriptId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取角色列表
     * 获取指定剧本的角色列表
     * @param scriptId
     * @param skip 跳过的记录数
     * @param limit 返回的记录数
     * @returns APIResponse_list_ScriptCharacter__ Successful Response
     * @throws ApiError
     */
    public static getCharactersApiCharactersScriptIdCharactersGet(
        scriptId: number,
        skip?: number,
        limit: number = 10,
    ): CancelablePromise<APIResponse_list_ScriptCharacter__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/characters/{script_id}/characters',
            path: {
                'script_id': scriptId,
            },
            query: {
                'skip': skip,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新角色
     * 更新指定角色的信息
     * @param scriptId
     * @param characterId
     * @param requestBody
     * @returns APIResponse_ScriptCharacter_ Successful Response
     * @throws ApiError
     */
    public static updateCharacterApiCharactersScriptIdCharactersCharacterIdPut(
        scriptId: number,
        characterId: number,
        requestBody: CharacterUpdateRequest,
    ): CancelablePromise<APIResponse_ScriptCharacter_> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/characters/{script_id}/characters/{character_id}',
            path: {
                'script_id': scriptId,
                'character_id': characterId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除角色
     * 删除指定角色
     * @param scriptId
     * @param characterId
     * @returns APIResponse_dict_ Successful Response
     * @throws ApiError
     */
    public static deleteCharacterApiCharactersScriptIdCharactersCharacterIdDelete(
        scriptId: number,
        characterId: number,
    ): CancelablePromise<APIResponse_dict_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/characters/{script_id}/characters/{character_id}',
            path: {
                'script_id': scriptId,
                'character_id': characterId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取角色详情
     * 获取指定角色的详细信息
     * @param scriptId
     * @param characterId
     * @returns APIResponse_ScriptCharacter_ Successful Response
     * @throws ApiError
     */
    public static getCharacterApiCharactersScriptIdCharactersCharacterIdGet(
        scriptId: number,
        characterId: number,
    ): CancelablePromise<APIResponse_ScriptCharacter_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/characters/{script_id}/characters/{character_id}',
            path: {
                'script_id': scriptId,
                'character_id': characterId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 生成角色头像提示词
     * 使用LLM生成角色头像的提示词
     * @param requestBody
     * @returns APIResponse_dict_ Successful Response
     * @throws ApiError
     */
    public static generateCharacterPromptApiCharactersCharactersGeneratePromptPost(
        requestBody: CharacterPromptRequest,
    ): CancelablePromise<APIResponse_dict_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/characters/characters/generate-prompt',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建场景
     * 为指定剧本创建新场景
     * @param scriptId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createLocationApiLocationsScriptIdLocationsPost(
        scriptId: number,
        requestBody: ScriptLocation,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/locations/{script_id}/locations',
            path: {
                'script_id': scriptId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取场景列表
     * 获取指定剧本的所有场景
     * @param scriptId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getLocationsApiLocationsScriptIdLocationsGet(
        scriptId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/locations/{script_id}/locations',
            path: {
                'script_id': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新场景
     * 更新指定场景的信息
     * @param scriptId
     * @param locationId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateLocationApiLocationsScriptIdLocationsLocationIdPut(
        scriptId: number,
        locationId: number,
        requestBody: ScriptLocation,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/locations/{script_id}/locations/{location_id}',
            path: {
                'script_id': scriptId,
                'location_id': locationId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除场景
     * 删除指定场景
     * @param scriptId
     * @param locationId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteLocationApiLocationsScriptIdLocationsLocationIdDelete(
        scriptId: number,
        locationId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/locations/{script_id}/locations/{location_id}',
            path: {
                'script_id': scriptId,
                'location_id': locationId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取场景详情
     * 获取指定场景的详细信息
     * @param scriptId
     * @param locationId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getLocationDetailApiLocationsScriptIdLocationsLocationIdGet(
        scriptId: number,
        locationId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/locations/{script_id}/locations/{location_id}',
            path: {
                'script_id': scriptId,
                'location_id': locationId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 生成场景图片提示词
     * 使用LLM生成场景图片的提示词
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static generateLocationPromptApiLocationsLocationsGeneratePromptPost(
        requestBody: LocationPromptRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/locations/locations/generate-prompt',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upload File
     * 文件上传API
     *
     * Args:
     * file: 上传的文件
     * category: 文件分类 (covers/avatars/evidence/scenes/general)
     *
     * Returns:
     * 上传结果和文件访问URL
     * @param formData
     * @param category
     * @returns any Successful Response
     * @throws ApiError
     */
    public static uploadFileApiFilesUploadPost(
        formData: Body_upload_file_api_files_upload_post,
        category: string = 'general',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/files/upload',
            query: {
                'category': category,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Files
     * 获取文件列表API
     *
     * Args:
     * category: 文件分类过滤 (可选)
     *
     * Returns:
     * 文件列表
     * @param category
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listFilesApiFilesListGet(
        category?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/files/list',
            query: {
                'category': category,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete File
     * 删除文件API
     *
     * Args:
     * file_url: 要删除的文件URL
     *
     * Returns:
     * 删除结果
     * @param fileUrl
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteFileApiFilesDeleteDelete(
        fileUrl: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/files/delete',
            query: {
                'file_url': fileUrl,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Storage Stats
     * 获取存储统计信息API
     *
     * Returns:
     * 存储统计数据
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getStorageStatsApiFilesStatsGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/files/stats',
        });
    }
    /**
     * Download File
     * 文件下载API
     *
     * Args:
     * file_path: 文件在MinIO中的路径
     *
     * Returns:
     * 文件流响应
     * @param filePath
     * @returns any Successful Response
     * @throws ApiError
     */
    public static downloadFileApiFilesDownloadFilePathGet(
        filePath: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/files/download/{file_path}',
            path: {
                'file_path': filePath,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Assets
     * 通过storage接口获取MinIO文件
     * @param path
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAssetsJubenshaAssetsPathGet(
        path: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/jubensha-assets/{path}',
            path: {
                'path': path,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 发送手机验证码
     * @param requestBody
     * @returns SmsCodeResponse Successful Response
     * @throws ApiError
     */
    public static sendSmsCodeApiAuthSmsCodePost(
        requestBody: SmsCodeRequest,
    ): CancelablePromise<SmsCodeResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/sms-code',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 手机号验证码登录或首次注册
     * @param requestBody
     * @returns Token Successful Response
     * @throws ApiError
     */
    public static phoneLoginApiAuthPhoneLoginPost(
        requestBody: PhoneLogin,
    ): CancelablePromise<Token> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/phone-login',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 用续期凭条换取新的访问令牌
     * 访问令牌到期后在后台静默换新，使用者无需重新登录。
     *
     * 换发时会挂失用过的这张续期凭条并下发新的一张，因此同一张凭条只能用一次；
     * 凭条被盗用后，真实用户的下一次换发就会失败，异常可以被发现。
     * @param requestBody
     * @returns Token Successful Response
     * @throws ApiError
     */
    public static refreshAccessTokenApiAuthRefreshPost(
        requestBody: RefreshRequest,
    ): CancelablePromise<Token> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/refresh',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 匿名登录
     * 匿名登录 — 仅在 ALLOW_ANONYMOUS_ACCESS=true 时可用，自动以默认访客账户登录
     * @returns Token Successful Response
     * @throws ApiError
     */
    public static anonymousLoginApiAuthAnonymousLoginPost(): CancelablePromise<Token> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/anonymous-login',
        });
    }
    /**
     * 用户注册
     * 用户注册
     * @param requestBody
     * @returns UserResponse Successful Response
     * @throws ApiError
     */
    public static registerApiAuthRegisterPost(
        requestBody: UserRegister,
    ): CancelablePromise<UserResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/register',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 用户登录
     * 用户登录
     * @param requestBody
     * @returns Token Successful Response
     * @throws ApiError
     */
    public static loginApiAuthLoginPost(
        requestBody: UserLogin,
    ): CancelablePromise<Token> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/login',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取当前用户信息
     * 获取当前用户信息（由认证中间件注入）
     * @returns UserResponse Successful Response
     * @throws ApiError
     */
    public static getCurrentUserInfoApiAuthMeGet(): CancelablePromise<UserResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/me',
        });
    }
    /**
     * 更新用户资料
     * 更新用户资料
     * @param requestBody
     * @returns UserResponse Successful Response
     * @throws ApiError
     */
    public static updateProfileApiAuthMePut(
        requestBody: UserUpdate,
    ): CancelablePromise<UserResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/auth/me',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 修改密码
     * 修改密码
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static changePasswordApiAuthChangePasswordPost(
        requestBody: PasswordChange,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/change-password',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 用户登出
     * 用户登出，并让本次使用的令牌立即失效。
     *
     * 此前登出只是让前端把令牌删掉，那枚令牌在服务端依然被接受，
     * 泄露后无法收回。现在会把它的编号写进挂失名单，剩余有效期内一律拒绝。
     * @returns any Successful Response
     * @throws ApiError
     */
    public static logoutApiAuthLogoutPost(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/auth/logout',
        });
    }
    /**
     * 获取用户列表
     * 获取用户列表（由认证中间件验证管理员权限）
     * @param skip
     * @param limit
     * @returns UserBrief Successful Response
     * @throws ApiError
     */
    public static getUsersApiAuthUsersGet(
        skip?: number,
        limit: number = 20,
    ): CancelablePromise<Array<UserBrief>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/users',
            query: {
                'skip': skip,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取指定用户信息
     * 获取指定用户信息
     * @param userId
     * @returns UserBrief Successful Response
     * @throws ApiError
     */
    public static getUserByIdApiAuthUsersUserIdGet(
        userId: number,
    ): CancelablePromise<UserBrief> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/users/{user_id}',
            path: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 验证令牌
     * 验证令牌有效性
     * @returns any Successful Response
     * @throws ApiError
     */
    public static verifyTokenApiAuthVerifyTokenGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/auth/verify-token',
        });
    }
    /**
     * Published Scripts
     * @returns any Successful Response
     * @throws ApiError
     */
    public static publishedScriptsApiFusionScriptsGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/scripts',
        });
    }
    /**
     * Create Session
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createSessionApiFusionSessionsPost(
        requestBody: CreateFusionSessionRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/sessions',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Session State
     * @param sessionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static sessionStateApiFusionSessionsSessionIdGet(
        sessionId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/sessions/{session_id}',
            path: {
                'session_id': sessionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Select Character
     * @param sessionId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static selectCharacterApiFusionSessionsSessionIdSelectCharacterPost(
        sessionId: string,
        requestBody: SelectCharacterRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/sessions/{session_id}/select-character',
            path: {
                'session_id': sessionId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Perform Action
     * @param sessionId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static performActionApiFusionSessionsSessionIdActionsPost(
        sessionId: string,
        requestBody: FusionActionRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/sessions/{session_id}/actions',
            path: {
                'session_id': sessionId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Session Events
     * @param sessionId
     * @param after
     * @returns any Successful Response
     * @throws ApiError
     */
    public static sessionEventsApiFusionSessionsSessionIdEventsGet(
        sessionId: string,
        after?: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/sessions/{session_id}/events',
            path: {
                'session_id': sessionId,
            },
            query: {
                'after': after,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Validate Script
     * @param scriptId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static validateScriptApiAdminFusionScriptsScriptIdValidatePost(
        scriptId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/scripts/{script_id}/validate',
            path: {
                'script_id': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Review Script
     * @param scriptId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static reviewScriptApiAdminFusionScriptsScriptIdReviewPost(
        scriptId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/scripts/{script_id}/review',
            path: {
                'script_id': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Publish Script
     * @param scriptId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static publishScriptApiAdminFusionScriptsScriptIdPublishPost(
        scriptId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/scripts/{script_id}/publish',
            path: {
                'script_id': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Archive Script
     * @param scriptId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static archiveScriptApiAdminFusionScriptsScriptIdArchivePost(
        scriptId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/scripts/{script_id}/archive',
            path: {
                'script_id': scriptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit Package
     * @returns any Successful Response
     * @throws ApiError
     */
    public static submitPackageApiAdminFusionScriptImportsPost(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/script-imports',
        });
    }
    /**
     * Get Import Job
     * @param jobId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getImportJobApiAdminFusionScriptImportsJobIdGet(
        jobId: number,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/script-imports/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Candidate Version
     * @param versionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCandidateVersionApiAdminFusionScriptPackagesVersionIdGet(
        versionId: number,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/script-packages/{version_id}',
            path: {
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Sources
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listSourcesApiAdminFusionSourceBundlesGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/source-bundles',
        });
    }
    /**
     * Get Bundle
     * @param bundleHash
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getBundleApiAdminFusionSourceBundlesBundleHashGet(
        bundleHash: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/source-bundles/{bundle_hash}',
            path: {
                'bundle_hash': bundleHash,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Source
     * @param bundleHash
     * @param sourceId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readSourceApiAdminFusionSourceBundlesBundleHashSourcesSourceIdGet(
        bundleHash: string,
        sourceId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/source-bundles/{bundle_hash}/sources/{source_id}',
            path: {
                'bundle_hash': bundleHash,
                'source_id': sourceId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Verify Bundle
     * @param bundleHash
     * @returns any Successful Response
     * @throws ApiError
     */
    public static verifyBundleApiAdminFusionSourceBundlesBundleHashVerifyPost(
        bundleHash: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/source-bundles/{bundle_hash}/verify',
            path: {
                'bundle_hash': bundleHash,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Verification
     * @param reportHash
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getVerificationApiAdminFusionSourceVerificationsReportHashGet(
        reportHash: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/source-verifications/{report_hash}',
            path: {
                'report_hash': reportHash,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Verify Candidate
     * @param versionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static verifyCandidateApiAdminFusionScriptPackagesVersionIdVerifySourcesPost(
        versionId: number,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/script-packages/{version_id}/verify-sources',
            path: {
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Candidates
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listCandidatesApiAdminFusionReviewCandidatesGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/review-candidates',
        });
    }
    /**
     * Read Review
     * @param versionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readReviewApiAdminFusionScriptPackagesVersionIdReviewGet(
        versionId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/script-packages/{version_id}/review',
            path: {
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Rule Review
     * @param versionId
     * @param bundleHash
     * @param expectedPackageHash
     * @param offset
     * @param limit
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readRuleReviewApiAdminFusionScriptPackagesVersionIdRuleReviewGet(
        versionId: string,
        bundleHash: string,
        expectedPackageHash: string,
        offset?: number,
        limit: number = 20,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/script-packages/{version_id}/rule-review',
            path: {
                'version_id': versionId,
            },
            query: {
                'bundle_hash': bundleHash,
                'expected_package_hash': expectedPackageHash,
                'offset': offset,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit Audit
     * @param versionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static submitAuditApiAdminFusionScriptPackagesVersionIdAuditsPost(
        versionId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/script-packages/{version_id}/audits',
            path: {
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add Disposition
     * @param auditId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static addDispositionApiAdminFusionScriptAuditsAuditIdDispositionsPost(
        auditId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/script-audits/{audit_id}/dispositions',
            path: {
                'audit_id': auditId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Jobs
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listJobsApiAdminFusionAuthoringJobsGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/authoring-jobs',
        });
    }
    /**
     * Create Job
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createJobApiAdminFusionAuthoringJobsPost(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/authoring-jobs',
        });
    }
    /**
     * Create Job
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createJobApiAdminFusionAuthoringJobsWithRulePlanPost(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/authoring-jobs/with-rule-plan',
        });
    }
    /**
     * Get Job
     * @param jobId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getJobApiAdminFusionAuthoringJobsJobIdGet(
        jobId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/authoring-jobs/{job_id}',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Cancel Job
     * @param jobId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static cancelJobApiAdminFusionAuthoringJobsJobIdCancelPost(
        jobId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/authoring-jobs/{job_id}/cancel',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Recover Job
     * @param jobId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static recoverJobApiAdminFusionAuthoringJobsJobIdRecoverPost(
        jobId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/authoring-jobs/{job_id}/recover',
            path: {
                'job_id': jobId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Publication State
     * @param versionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static publicationStateApiAdminFusionScriptPackagesVersionIdPublicationGet(
        versionId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/fusion/script-packages/{version_id}/publication',
            path: {
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Approve Publication
     * @param versionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static approvePublicationApiAdminFusionScriptPackagesVersionIdApprovalsPost(
        versionId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/script-packages/{version_id}/approvals',
            path: {
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Publish Package
     * @param versionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static publishPackageApiAdminFusionScriptPackagesVersionIdPublishPost(
        versionId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/fusion/script-packages/{version_id}/publish',
            path: {
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Releases
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listReleasesApiFusionPackageReleasesGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-releases',
        });
    }
    /**
     * Create Session
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createSessionApiFusionPackageSessionsPost(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-sessions',
        });
    }
    /**
     * Get Session
     * @param sessionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getSessionApiFusionPackageSessionsSessionIdGet(
        sessionId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-sessions/{session_id}',
            path: {
                'session_id': sessionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Opening Image
     * @param sessionId
     * @param visualId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getOpeningImageApiFusionPackageSessionsSessionIdImagesVisualIdGet(
        sessionId: string,
        visualId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-sessions/{session_id}/images/{visual_id}',
            path: {
                'session_id': sessionId,
                'visual_id': visualId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Find Flow
     * @param openingSessionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static findFlowApiFusionPackageFlowsGet(
        openingSessionId: string = '',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-flows',
            query: {
                'opening_session_id': openingSessionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Flow
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createFlowApiFusionPackageFlowsPost(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-flows',
        });
    }
    /**
     * Read Flow
     * @param flowId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readFlowApiFusionPackageFlowsFlowIdGet(
        flowId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-flows/{flow_id}',
            path: {
                'flow_id': flowId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Act Flow
     * @param flowId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static actFlowApiFusionPackageFlowsFlowIdActionsPost(
        flowId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-flows/{flow_id}/actions',
            path: {
                'flow_id': flowId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Decide Role
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static decideRoleApiFusionPackagePlaysPlayIdDecisionsPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/decisions',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Private Response
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static privateResponseApiFusionPackagePlaysPlayIdPrivateResponsesPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/private-responses',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Phone Step
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static phoneStepApiFusionPackagePlaysPlayIdPhoneStepPost(
        playId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/phone-step',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Phone Pause
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static phonePauseApiFusionPackagePlaysPlayIdPhonePausePost(
        playId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/phone-pause',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Play Library
     * @param offset
     * @param limit
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listPlayLibraryApiFusionPackagePlayLibraryGet(
        offset: string = '0',
        limit: string = '20',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-play-library',
            query: {
                'offset': offset,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Find Play
     * @param openingSessionId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static findPlayApiFusionPackagePlaysGet(
        openingSessionId: string = '',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-plays',
            query: {
                'opening_session_id': openingSessionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Play
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createPlayApiFusionPackagePlaysPost(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays',
        });
    }
    /**
     * Read Play
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readPlayApiFusionPackagePlaysPlayIdGet(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-plays/{play_id}',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Play Image
     * @param playId
     * @param visualId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readPlayImageApiFusionPackagePlaysPlayIdImagesVisualIdGet(
        playId: string,
        visualId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-plays/{play_id}/images/{visual_id}',
            path: {
                'play_id': playId,
                'visual_id': visualId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Act Play
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static actPlayApiFusionPackagePlaysPlayIdActionsPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/actions',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Ask Role
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static askRoleApiFusionPackagePlaysPlayIdAskPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/ask',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Speak Play
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static speakPlayApiFusionPackagePlaysPlayIdDiscussionPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/discussion',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Propose Investigation
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static proposeInvestigationApiFusionPackagePlaysPlayIdProposalsPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/proposals',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Respond Role
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static respondRoleApiFusionPackagePlaysPlayIdResponsesPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/responses',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Table Action
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static tableActionApiFusionPackagePlaysPlayIdTablePost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/table',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Guided Play
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static guidedPlayApiFusionPackagePlaysPlayIdGuidedPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/guided',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Topic Play
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static topicPlayApiFusionPackagePlaysPlayIdTopicPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/topic',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Complete Finale Motivations
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static completeFinaleMotivationsApiFusionPackagePlaysPlayIdFinaleMotivationsPost(
        playId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/finale-motivations',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Availability
     * @param playId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static availabilityApiFusionPackagePlaysPlayIdSpeechInputGet(
        playId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-plays/{play_id}/speech-input',
            path: {
                'play_id': playId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Stream Ticket
     * @param playId
     * @param requestId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static streamTicketApiFusionPackagePlaysPlayIdSpeechStreamRequestIdTicketPost(
        playId: string,
        requestId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/speech-stream/{request_id}/ticket',
            path: {
                'play_id': playId,
                'request_id': requestId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Receipt
     * @param playId
     * @param requestId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static receiptApiFusionPackagePlaysPlayIdSpeechInputRequestIdGet(
        playId: string,
        requestId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/fusion/package-plays/{play_id}/speech-input/{request_id}',
            path: {
                'play_id': playId,
                'request_id': requestId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Transcribe
     * @param playId
     * @param requestId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static transcribeApiFusionPackagePlaysPlayIdSpeechInputRequestIdPost(
        playId: string,
        requestId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/fusion/package-plays/{play_id}/speech-input/{request_id}',
            path: {
                'play_id': playId,
                'request_id': requestId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
