using System;
using MediaBrowser.Controller;
using MediaBrowser.Controller.Plugins;
using Microsoft.Extensions.DependencyInjection;
using Jellyfin.Plugin.MissingEpisodeAlert.Services;

namespace Jellyfin.Plugin.MissingEpisodeAlert;

/// <summary>
/// Plugin service registrator for dependency injection.
/// </summary>
public class PluginServiceRegistrator : IPluginServiceRegistrator
{
    /// <inheritdoc />
    public void RegisterServices(IServiceCollection serviceCollection, IServerApplicationHost applicationHost)
    {
        serviceCollection.AddSingleton<MissingEpisodeDetectionService>();
        serviceCollection.AddSingleton<NotificationService>();
        serviceCollection.AddSingleton<PlaybackMonitorService>();
        
        // Initialize plugin services after registration
        serviceCollection.AddSingleton<IPluginServiceInitializer, PluginServiceInitializer>();
    }
}

/// <summary>
/// Service initializer for the plugin.
/// </summary>
public interface IPluginServiceInitializer
{
    /// <summary>
    /// Initialize plugin services.
    /// </summary>
    void Initialize();
}

/// <summary>
/// Implementation of plugin service initializer.
/// </summary>
public class PluginServiceInitializer : IPluginServiceInitializer
{
    private readonly IServiceProvider _serviceProvider;

    /// <summary>
    /// Initializes a new instance of the <see cref="PluginServiceInitializer"/> class.
    /// </summary>
    /// <param name="serviceProvider">The service provider.</param>
    public PluginServiceInitializer(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
    }

    /// <inheritdoc />
    public void Initialize()
    {
        Plugin.Instance?.InitializeServices(_serviceProvider);
    }
}
