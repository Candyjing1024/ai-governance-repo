using System.Net;
using System.Text.Json;
using ProjectManagementAPI.Exceptions;

namespace ProjectManagementAPI.Middleware;

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
            ArgumentException or FormatException => (HttpStatusCode.BadRequest, "Invalid request parameters."),
            UnauthorizedAccessException => (HttpStatusCode.Unauthorized, "Authentication is required."),
            KeyNotFoundException => (HttpStatusCode.NotFound, "The requested resource was not found."),
            TimeoutException => (HttpStatusCode.RequestTimeout, "The request timed out."),
            OperationCanceledException => (HttpStatusCode.ServiceUnavailable, "The request was cancelled."),
            _ => (HttpStatusCode.InternalServerError, "An unexpected error occurred.")
        };

        _logger.LogError(exception, "Unhandled exception. StatusCode: {StatusCode}", (int)statusCode);

        context.Response.StatusCode = (int)statusCode;
        context.Response.ContentType = "application/json";

        var response = new
        {
            statusCode = (int)statusCode,
            message,
            traceId = context.TraceIdentifier
        };

        await context.Response.WriteAsync(JsonSerializer.Serialize(response,
            new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase }));
    }
}
