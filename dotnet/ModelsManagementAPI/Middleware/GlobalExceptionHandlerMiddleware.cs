using System.Net;
using System.Text.Json;
using Microsoft.Azure.Cosmos;
using ModelsManagementAPI.Exceptions;

namespace ModelsManagementAPI.Middleware;

public class GlobalExceptionHandlerMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<GlobalExceptionHandlerMiddleware> _logger;

    public GlobalExceptionHandlerMiddleware(RequestDelegate next, ILogger<GlobalExceptionHandlerMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            await HandleExceptionAsync(context, ex);
        }
    }

    private async Task HandleExceptionAsync(HttpContext context, Exception exception)
    {
        var (statusCode, message) = exception switch
        {
            // Custom API exceptions — thrown from any layer (controllers, services, etc.)
            ApiException apiEx => (apiEx.StatusCode, apiEx.Message),

            // ASP.NET Core bad request exceptions
            BadHttpRequestException badReq => ((HttpStatusCode)badReq.StatusCode, badReq.Message),

            // Cosmos DB exceptions — mapped by HTTP status code
            CosmosException cosmosEx => cosmosEx.StatusCode switch
            {
                HttpStatusCode.BadRequest => (HttpStatusCode.BadRequest, "The request was invalid or malformed."),
                HttpStatusCode.Unauthorized => (HttpStatusCode.Unauthorized, "Authentication is required to access this resource."),
                HttpStatusCode.Forbidden => (HttpStatusCode.Forbidden, "You do not have permission to perform this action."),
                HttpStatusCode.NotFound => (HttpStatusCode.NotFound, "The requested resource was not found."),
                HttpStatusCode.MethodNotAllowed => (HttpStatusCode.MethodNotAllowed, "The HTTP method is not allowed for this resource."),
                HttpStatusCode.Conflict => (HttpStatusCode.Conflict, "A resource with the same identifier already exists."),
                HttpStatusCode.TooManyRequests => (HttpStatusCode.ServiceUnavailable, "The service is temporarily unavailable. Please retry later."),
                _ => (cosmosEx.StatusCode, "A database error occurred. Please try again later.")
            },

            // Common .NET exceptions
            ArgumentException or FormatException
                => (HttpStatusCode.BadRequest, "Invalid request parameters."),

            UnauthorizedAccessException
                => (HttpStatusCode.Unauthorized, "Authentication is required to access this resource."),

            KeyNotFoundException
                => (HttpStatusCode.NotFound, "The requested resource was not found."),

            NotSupportedException
                => (HttpStatusCode.MethodNotAllowed, "The requested operation is not supported."),

            InvalidOperationException
                => (HttpStatusCode.Conflict, "The operation is not valid for the current state of the resource."),

            TimeoutException
                => (HttpStatusCode.RequestTimeout, "The request timed out. Please try again."),

            OperationCanceledException
                => (HttpStatusCode.ServiceUnavailable, "The request was cancelled or timed out."),

            _ => (HttpStatusCode.InternalServerError, "An unexpected error occurred. Please try again later.")
        };

        _logger.LogError(exception, "Unhandled exception caught by global handler. StatusCode: {StatusCode}", (int)statusCode);

        context.Response.StatusCode = (int)statusCode;
        context.Response.ContentType = "application/json";

        var response = new ErrorResponse
        {
            StatusCode = (int)statusCode,
            Message = message,
            TraceId = context.TraceIdentifier
        };

        var json = JsonSerializer.Serialize(response, new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        });

        await context.Response.WriteAsync(json);
    }
}

public class ErrorResponse
{
    public int StatusCode { get; set; }
    public string Message { get; set; } = string.Empty;
    public string TraceId { get; set; } = string.Empty;
}
