using System.Net;

namespace UserManagementAPI.Exceptions;

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
