using System.Net;
using System.Text.Json;
using AgentManagementAPI.Exceptions;

namespace AgentManagementAPI.Middleware;

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
            ApiException apiEx => (apiEx.StatusCode, apiEx.Message),
            BadHttpRequestException badReq => ((HttpStatusCode)badReq.StatusCode, badReq.Message),
            ArgumentException or FormatException
                => (HttpStatusCode.BadRequest, "Invalid request parameters."),
            UnauthorizedAccessException
                => (HttpStatusCode.Unauthorized, "Authentication is required to access this resource."),
            KeyNotFoundException
                => (HttpStatusCode.NotFound, "The requested resource was not found."),
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
