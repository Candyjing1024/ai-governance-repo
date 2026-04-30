using System.Net;

namespace ModelsManagementAPI.Exceptions;

public class ApiException : Exception
{
    public HttpStatusCode StatusCode { get; }

    public ApiException(HttpStatusCode statusCode, string message) : base(message)
    {
        StatusCode = statusCode;
    }
}

public class BadRequestException : ApiException
{
    public BadRequestException(string message = "The request was invalid or malformed.")
        : base(HttpStatusCode.BadRequest, message) { }
}

public class UnauthorizedException : ApiException
{
    public UnauthorizedException(string message = "Authentication is required to access this resource.")
        : base(HttpStatusCode.Unauthorized, message) { }
}

public class ForbiddenException : ApiException
{
    public ForbiddenException(string message = "You do not have permission to perform this action.")
        : base(HttpStatusCode.Forbidden, message) { }
}

public class NotFoundException : ApiException
{
    public NotFoundException(string message = "The requested resource was not found.")
        : base(HttpStatusCode.NotFound, message) { }
}

public class ConflictException : ApiException
{
    public ConflictException(string message = "A resource with the same identifier already exists.")
        : base(HttpStatusCode.Conflict, message) { }
}
